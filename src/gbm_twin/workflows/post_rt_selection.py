from __future__ import annotations

import csv
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, median
from typing import TypedDict, cast

from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
    TreatmentRecord,
)
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.post_rt_selection_config import (
    PostRTSelectionConfig,
    load_post_rt_selection_config,
)
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.workflows.calibration import (
    V2_ALPHA_BETA_RATIO_GY,
    V2_EFFECTIVE_ALPHA_PER_GY,
    calibrate_v2_interval,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
    prepare_patient_timepoint,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
    v2_calibration_config_sha256,
)
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.single_patient import (
    calibration_config_from_experiment,
)
from gbm_twin.workflows.treatment_protocol import (
    PostRadiotherapyConfig,
    reconstruct_patient_treatment,
)

POST_RT_SELECTION_ARTIFACT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PostRTCandidate:
    candidate_id: str
    initial_kill_rate_per_day: float | None
    decay_time_days: float | None

    @property
    def is_fractionated_only_baseline(self) -> bool:
        return (
            self.initial_kill_rate_per_day is None
            and self.decay_time_days is None
        )


@dataclass(frozen=True)
class PostRTPatientCalibration:
    patient_id: int
    candidate_id: str

    initial_kill_rate_per_day: float | None
    decay_time_days: float | None

    last_fraction_day: float
    days_last_fraction_to_t1: float

    diffusion: float
    proliferation: float

    calibration_dice: float
    calibration_volume_error: float
    calibration_loss: float

    calibration_identifiable: bool
    calibration_at_boundary: bool


@dataclass(frozen=True)
class PostRTCandidateSummary:
    candidate_id: str
    initial_kill_rate_per_day: float | None
    decay_time_days: float | None

    patient_count: int

    mean_calibration_loss: float
    median_calibration_loss: float
    mean_calibration_dice: float
    median_calibration_dice: float

    calibration_boundary_count: int
    calibration_non_identifiable_count: int


@dataclass(frozen=True)
class _PreparedSelectionPatient:
    patient_id: int
    treatment_record: TreatmentRecord
    start: PreparedPatientTimepoint
    observed: PreparedPatientTimepoint


class PostRTExcludedPatient(TypedDict):
    patient_id: int
    reason: str


@dataclass(frozen=True)
class PostRTSelectionResult:
    directory: Path
    manifest: dict[str, object]


def _candidate_id(
    *,
    kill_rate: float,
    decay_time_days: float,
) -> str:
    return (
        "post-rt-"
        f"k{kill_rate:.6g}-"
        f"tau{decay_time_days:.6g}"
    )


def build_post_rt_candidates(
    config: PostRTSelectionConfig,
) -> tuple[PostRTCandidate, ...]:
    candidates: list[PostRTCandidate] = []

    if config.include_fractionated_only_baseline:
        candidates.append(
            PostRTCandidate(
                candidate_id="fractionated-only",
                initial_kill_rate_per_day=None,
                decay_time_days=None,
            )
        )

    for kill_rate in config.initial_kill_rates_per_day:
        for decay_time in config.decay_times_days:
            candidates.append(
                PostRTCandidate(
                    candidate_id=_candidate_id(
                        kill_rate=kill_rate,
                        decay_time_days=decay_time,
                    ),
                    initial_kill_rate_per_day=kill_rate,
                    decay_time_days=decay_time,
                )
            )

    if not candidates:
        raise ValueError(
            "Post-RT selection produced no candidates"
        )

    return tuple(candidates)


def _post_rt_config(
    candidate: PostRTCandidate,
) -> PostRadiotherapyConfig | None:
    if candidate.is_fractionated_only_baseline:
        return None

    kill_rate = candidate.initial_kill_rate_per_day
    decay_time = candidate.decay_time_days

    if kill_rate is None or decay_time is None:
        raise ValueError(
            f"Candidate {candidate.candidate_id} is incomplete"
        )

    return PostRadiotherapyConfig(
        initial_kill_rate_per_day=kill_rate,
        decay_time_days=decay_time,
    )


def _summarize_candidate(
    candidate: PostRTCandidate,
    rows: list[PostRTPatientCalibration],
) -> PostRTCandidateSummary:
    selected = [
        row
        for row in rows
        if row.candidate_id == candidate.candidate_id
    ]

    if not selected:
        raise ValueError(
            f"Candidate {candidate.candidate_id} has no patient results"
        )

    losses = [
        row.calibration_loss
        for row in selected
    ]

    dice_values = [
        row.calibration_dice
        for row in selected
    ]

    return PostRTCandidateSummary(
        candidate_id=candidate.candidate_id,
        initial_kill_rate_per_day=(
            candidate.initial_kill_rate_per_day
        ),
        decay_time_days=(
            candidate.decay_time_days
        ),
        patient_count=len(selected),
        mean_calibration_loss=float(
            fmean(losses)
        ),
        median_calibration_loss=float(
            median(losses)
        ),
        mean_calibration_dice=float(
            fmean(dice_values)
        ),
        median_calibration_dice=float(
            median(dice_values)
        ),
        calibration_boundary_count=sum(
            row.calibration_at_boundary
            for row in selected
        ),
        calibration_non_identifiable_count=sum(
            not row.calibration_identifiable
            for row in selected
        ),
    )


def _selection_key(
    summary: PostRTCandidateSummary,
) -> tuple[float, float, int, int, str]:
    return (
        summary.mean_calibration_loss,
        summary.median_calibration_loss,
        summary.calibration_boundary_count,
        summary.calibration_non_identifiable_count,
        summary.candidate_id,
    )


def _write_candidate_csv(
    path: Path,
    summaries: list[PostRTCandidateSummary],
) -> None:
    columns = tuple(
        PostRTCandidateSummary.__dataclass_fields__
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            lineterminator="\n",
        )
        writer.writeheader()

        for summary in summaries:
            writer.writerow(
                asdict(summary)
            )


def _write_patient_csv(
    path: Path,
    rows: list[PostRTPatientCalibration],
) -> None:
    columns = tuple(
        PostRTPatientCalibration.__dataclass_fields__
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(columns),
            lineterminator="\n",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                asdict(row)
            )


def select_post_rt_parameters(
    *,
    experiment_config_path: Path,
    selection_config_path: Path,
    repo_root: Path,
    cache_root: Path,
    output_dir: Path,
    workers: int = 1,
    allow_dirty: bool = False,
) -> PostRTSelectionResult:
    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    destination = output_dir.resolve()

    if destination.exists():
        raise FileExistsError(
            "Post-RT selection destination already exists: "
            f"{destination}"
        )

    experiment = load_cohort_experiment_config(
        experiment_config_path
    )

    selection_config = load_post_rt_selection_config(
        selection_config_path
    )

    repository_state = read_repository_state(
        repo_root
    )

    if repository_state.dirty and not allow_dirty:
        raise ValueError(
            "Post-RT selection requires a clean Git working tree"
        )

    calibration_config = calibration_config_from_experiment(
        experiment
    )

    treatment_metadata = CFBTreatmentMetadata(
        experiment.metadata_root
    )

    radiobiology = RadiobiologyParameters(
        alpha_per_gy=V2_EFFECTIVE_ALPHA_PER_GY,
        alpha_beta_ratio_gy=V2_ALPHA_BETA_RATIO_GY,
    )

    candidates = build_post_rt_candidates(
        selection_config
    )

    prepared_patients: list[
        _PreparedSelectionPatient
    ] = []

    excluded: list[PostRTExcludedPatient] = []

    for patient_id in experiment.patient_ids:
        record = treatment_metadata.treatment(
            patient_id
        )

        if (
            record is None
            or record.radiotherapy_start_day is None
            or record.dose_gy is None
            or record.fractions_number is None
        ):
            excluded.append(
                {
                    "patient_id": patient_id,
                    "reason": "treatment_schedule_unavailable",
                }
            )
            continue

        start = prepare_patient_timepoint(
            metadata_root=experiment.metadata_root,
            patients_root=experiment.patients_root,
            patient_id=patient_id,
            timepoint_name="t0",
            target_spacing=experiment.evaluation.target_spacing,
        )

        observed = prepare_patient_timepoint(
            metadata_root=experiment.metadata_root,
            patients_root=experiment.patients_root,
            patient_id=patient_id,
            timepoint_name="t1",
            target_spacing=experiment.evaluation.target_spacing,
        )

        prepared_patients.append(
            _PreparedSelectionPatient(
                patient_id=patient_id,
                treatment_record=record,
                start=start,
                observed=observed,
            )
        )

    if not prepared_patients:
        raise ValueError(
            "No patients have reconstructable RT schedules"
        )

    rows: list[PostRTPatientCalibration] = []

    for candidate in candidates:
        post_rt = _post_rt_config(
            candidate
        )

        for prepared in prepared_patients:
            reconstructed = reconstruct_patient_treatment(
                prepared.treatment_record,
                radiobiology=radiobiology,
                post_rt=post_rt,
            )

            last_fraction_day = (
                reconstructed.schedule.fraction_days[-1]
            )

            calibration = calibrate_v2_interval(
                start=prepared.start,
                observed=prepared.observed,
                treatment=reconstructed.model,
                config=calibration_config,
                cache_dir=(
                    cache_root.resolve()
                    / f"patient-{prepared.patient_id}"
                ),
                workers=workers,
            )

            diagnostics = calibration.diagnostics

            rows.append(
                PostRTPatientCalibration(
                    patient_id=prepared.patient_id,
                    candidate_id=candidate.candidate_id,
                    initial_kill_rate_per_day=(
                        candidate.initial_kill_rate_per_day
                    ),
                    decay_time_days=(
                        candidate.decay_time_days
                    ),
                    last_fraction_day=(
                        last_fraction_day
                    ),
                    days_last_fraction_to_t1=(
                        prepared.observed.days_from_baseline
                        - last_fraction_day
                    ),
                    diffusion=calibration.best.diffusion,
                    proliferation=(
                        calibration.best.proliferation
                    ),
                    calibration_dice=calibration.best.dice,
                    calibration_volume_error=(
                        calibration.best.volume_error
                    ),
                    calibration_loss=calibration.best.loss,
                    calibration_identifiable=(
                        diagnostics.identifiable
                    ),
                    calibration_at_boundary=(
                        diagnostics.diffusion_at_boundary
                        or diagnostics.proliferation_at_boundary
                    ),
                )
            )

    summaries = [
        _summarize_candidate(
            candidate,
            rows,
        )
        for candidate in candidates
    ]

    summaries.sort(
        key=_selection_key
    )

    selected = summaries[0]

    payload: dict[str, object] = {
        "schema_version": (
            POST_RT_SELECTION_ARTIFACT_SCHEMA_VERSION
        ),
        "kind": "v3_post_rt_parameter_selection",
        "sealed": True,
        "leakage_control": {
            "uses_timepoints": [
                "t0",
                "t1",
            ],
            "loads_t2_imaging": False,
            "selection_metric": (
                "mean_t0_t1_calibration_loss"
            ),
        },
        "repository": {
            "commit_sha": repository_state.commit_sha,
            "dirty": repository_state.dirty,
        },
        "experiment": {
            "experiment_config_file": (
                experiment_config_path.name
            ),
            "experiment_config_sha256": (
                sha256_file(
                    experiment_config_path.resolve()
                )
            ),
            "selection_config_file": (
                selection_config_path.name
            ),
            "selection_config_sha256": (
                sha256_file(
                    selection_config_path.resolve()
                )
            ),
            "calibration_config_sha256": (
                v2_calibration_config_sha256(
                    calibration_config
                )
            ),
            "selected_patient_ids": list(
                experiment.patient_ids
            ),
        },
        "selected_candidate": asdict(
            selected
        ),
        "candidate_summaries": [
            asdict(summary)
            for summary in summaries
        ],
        "patient_results": [
            asdict(row)
            for row in rows
        ],
        "excluded_patients": excluded,
    }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )

    try:
        manifest_path = (
            temporary
            / "post_rt_selection.json"
        )

        manifest_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            temporary
            / "post_rt_selection.sha256"
        ).write_text(
            sha256_file(manifest_path)
            + "  post_rt_selection.json\n",
            encoding="ascii",
        )

        _write_candidate_csv(
            temporary
            / "post_rt_candidates.csv",
            summaries,
        )

        _write_patient_csv(
            temporary
            / "post_rt_patients.csv",
            rows,
        )

        temporary.rename(
            destination
        )

    except BaseException:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    raw_canonical: object = json.loads(
        (
            destination
            / "post_rt_selection.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(raw_canonical, dict):
        raise ValueError(
            "Post-RT selection artifact must be a JSON object"
        )

    canonical_payload = cast(
        dict[str, object],
        raw_canonical,
    )

    return PostRTSelectionResult(
        directory=destination,
        manifest=canonical_payload,
    )
