from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, median
from typing import cast

import numpy as np

from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.delayed_response import DelayedResponseParameters
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_patient import (
    Stage8EvaluationTarget,
    Stage8ForecastInputs,
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_protocol import load_stage8_protocol_config
from gbm_twin.workflows.stage8_selection_artifact import (
    SelectedStage8Model,
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage8_validation import (
    preflight_stage8_validation_inputs,
)
from gbm_twin.workflows.stage9_forecast import simulate_stage9_forecast
from gbm_twin.workflows.stage9_model_family import (
    Stage9DelayedCandidate,
    control_candidate,
    deduplicate_candidates,
    timescale_candidates,
    transfer_candidates,
    visibility_candidates,
)
from gbm_twin.workflows.stage9_protocol import (
    Stage9ProtocolConfig,
    load_stage9_protocol_config,
)

STAGE9_SELECTION_SCHEMA_VERSION = 1
STAGE9_SELECTION_DESIGN = "frozen_stage8_kinetics_delayed_response_v1"


@dataclass(frozen=True)
class FrozenStage8Kinetics:
    patient_id: int
    diffusion: float
    proliferation: float
    expected_stage8_dice: float
    source: str


@dataclass(frozen=True)
class Stage9PatientCandidateEvaluation:
    patient_id: int
    candidate_id: str
    damage_transfer_fraction: float
    damage_half_life_days: float
    damaged_visibility: float
    complexity_rank: int
    diffusion: float
    proliferation: float
    twin_dice: float
    persistence_dice: float
    delta_vs_persistence: float
    relative_volume_error: float
    persistence_relative_volume_error: float
    hd95_mm: float | None
    persistence_hd95_mm: float | None
    centroid_distance_mm: float | None
    persistence_centroid_distance_mm: float | None
    t1_day: float
    t2_day: float
    forecast_horizon_days: float
    days_last_rt_to_t1: float
    observed_t1_volume_cm3: float
    observed_t2_volume_cm3: float
    predicted_t2_volume_cm3: float
    observed_volume_change_fraction: float


@dataclass(frozen=True)
class Stage9CandidateSummary:
    candidate_id: str
    complexity_rank: int
    patient_count: int
    mean_dice: float
    median_dice: float
    mean_delta_vs_persistence: float
    median_delta_vs_persistence: float
    mean_relative_volume_error: float
    mean_hd95_mm: float | None
    catastrophic_failure_count: int
    better_count: int
    equal_count: int
    worse_count: int


@dataclass(frozen=True)
class Stage9SelectionArtifact:
    directory: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class _PreparedPatient:
    inputs: Stage8ForecastInputs
    target: Stage8EvaluationTarget
    observed_t2: np.ndarray
    persistence: np.ndarray
    persistence_dice: float
    persistence_relative_volume_error: float
    persistence_hd95_mm: float | None
    persistence_centroid_distance_mm: float | None


def _load_sealed_json(
    root: Path,
    *,
    basename: str,
) -> tuple[dict[str, object], str]:
    directory = root.resolve()
    manifest_path = directory / f"{basename}.json"
    seal_path = directory / f"{basename}.sha256"

    if not manifest_path.is_file() or not seal_path.is_file():
        raise FileNotFoundError(
            f"Incomplete sealed artifact: {directory}"
        )

    tokens = seal_path.read_text(encoding="ascii").split()
    actual = sha256_file(manifest_path)
    if not tokens or tokens[0] != actual:
        raise ValueError(f"Checksum mismatch for {manifest_path}")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{manifest_path} must contain a JSON object")
    return cast(dict[str, object], raw), actual


def _mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return cast(dict[str, object], value)


def _list(
    mapping: dict[str, object],
    key: str,
) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return cast(list[object], value)


def _int(value: object, *, name: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{name} must be an integer")
    return cast(int, value)


def _float(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _optional_mean(values: list[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return float(fmean(available)) if available else None


def _stage8_frozen_kinetics(
    *,
    stage8_selection_root: Path,
    stage8_validation_root: Path,
    selected: SelectedStage8Model,
) -> tuple[
    dict[int, FrozenStage8Kinetics],
    dict[str, object],
    dict[str, object],
    str,
    str,
]:
    selection, selection_sha = _load_sealed_json(
        stage8_selection_root,
        basename="stage8_model_selection",
    )
    validation, validation_sha = _load_sealed_json(
        stage8_validation_root,
        basename="stage8_internal_validation",
    )

    if selection.get("sealed") is not True:
        raise ValueError("Stage 8 model selection is not sealed")
    if validation.get("sealed") is not True:
        raise ValueError("Stage 8 internal validation is not sealed")

    validation_leakage = _mapping(validation, "leakage_control")
    if validation_leakage.get("internal_validation_t2_loaded") is not True:
        raise ValueError(
            "Stage 9 requires a completed Stage 8 internal validation"
        )
    if validation_leakage.get("untouched_holdout_t2_loaded") is not False:
        raise ValueError(
            "Stage 8 validation violated the untouched-holdout contract"
        )

    selected_payload = _mapping(selection, "selected_candidate")
    selected_id = selected_payload.get("candidate_id")
    if selected_id != selected.candidate.candidate_id:
        raise ValueError("Stage 8 selected-candidate mismatch")

    validation_selected = _mapping(validation, "selected_candidate")
    if validation_selected.get("candidate_id") != selected_id:
        raise ValueError(
            "Stage 8 validation used a different selected candidate"
        )

    kinetics: dict[int, FrozenStage8Kinetics] = {}
    selection_leakage = _mapping(selection, "leakage_control")
    development_ids = {
        _int(value, name="development patient ID")
        for value in _list(
            selection_leakage,
            "development_patient_ids",
        )
    }

    for raw in _list(selection, "patient_candidate_results"):
        if not isinstance(raw, dict):
            raise ValueError(
                "Stage 8 patient-candidate result must be a mapping"
            )
        row = cast(dict[str, object], raw)
        if row.get("candidate_id") != selected_id:
            continue
        patient_id = _int(row.get("patient_id"), name="patient_id")
        if patient_id not in development_ids:
            continue
        kinetics[patient_id] = FrozenStage8Kinetics(
            patient_id=patient_id,
            diffusion=_float(row.get("diffusion"), name="diffusion"),
            proliferation=_float(
                row.get("proliferation"),
                name="proliferation",
            ),
            expected_stage8_dice=_float(
                row.get("t2_dice"),
                name="t2_dice",
            ),
            source="stage8-development-selection",
        )

    validation_ids = {
        _int(value, name="validation patient ID")
        for value in _list(
            validation_leakage,
            "internal_validation_patient_ids",
        )
    }
    for raw in _list(validation, "patients"):
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 validation patient must be a mapping")
        row = cast(dict[str, object], raw)
        patient_id = _int(row.get("patient_id"), name="patient_id")
        if patient_id not in validation_ids:
            continue
        if patient_id in kinetics:
            raise ValueError(
                f"Patient {patient_id} appears in both Stage 8 cohorts"
            )
        kinetics[patient_id] = FrozenStage8Kinetics(
            patient_id=patient_id,
            diffusion=_float(row.get("diffusion"), name="diffusion"),
            proliferation=_float(
                row.get("proliferation"),
                name="proliferation",
            ),
            expected_stage8_dice=_float(
                row.get("twin_dice"),
                name="twin_dice",
            ),
            source="stage8-internal-validation",
        )

    expected_ids = development_ids | validation_ids
    if set(kinetics) != expected_ids:
        missing = sorted(expected_ids - set(kinetics))
        raise ValueError(
            "Missing frozen Stage 8 kinetics for patients: "
            + ", ".join(str(value) for value in missing)
        )

    return (
        kinetics,
        selection,
        validation,
        selection_sha,
        validation_sha,
    )


def _development_and_reserve_ids(
    audit_manifest: dict[str, object],
    *,
    development_ids: set[int],
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    holdout: set[int] = set()
    reserve: set[int] = set()

    for raw in _list(audit_manifest, "patients"):
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")
        row = cast(dict[str, object], raw)
        patient_id = _int(row.get("patient_id"), name="patient_id")
        split = row.get("split")

        if split == "untouched-holdout":
            holdout.add(patient_id)
            continue

        if (
            row.get("core_eligible") is True
            and row.get("exposed_development") is not True
            and split in {"development", "internal-validation"}
            and patient_id not in development_ids
        ):
            reserve.add(patient_id)

    if development_ids & holdout:
        raise ValueError(
            "Stage 9 development cohort intersects untouched holdout"
        )

    return (
        tuple(sorted(development_ids)),
        tuple(sorted(reserve)),
        tuple(sorted(holdout)),
    )


def _observation_parameters(
    stage8_protocol_path: Path,
) -> MRIDetectionObservationParameters:
    protocol = load_stage8_protocol_config(stage8_protocol_path)
    return MRIDetectionObservationParameters(
        enhancing_threshold=(
            protocol.observation.enhancing_detection_threshold
        ),
        infiltrative_threshold=(
            protocol.observation.infiltrative_detection_threshold
        ),
        transition_width_mm=protocol.observation.transition_width_mm,
    )


def _prepare_patients(
    *,
    patient_ids: tuple[int, ...],
    metadata_root: Path,
    patients_root: Path,
    target_spacing: tuple[float, float, float],
    treatment: CFBTreatmentMetadata,
    observation: MRIDetectionObservationParameters,
    load_spatial_rtdose: bool,
    progress: Callable[[str], None] | None,
) -> dict[int, _PreparedPatient]:
    prepared: dict[int, _PreparedPatient] = {}

    for index, patient_id in enumerate(patient_ids, start=1):
        if progress is not None:
            progress(
                f"[stage9] preparing patient {patient_id} "
                f"({index}/{len(patient_ids)})"
            )

        inputs = prepare_stage8_forecast_inputs(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=target_spacing,
            treatment=treatment,
            observation_parameters=observation,
            load_spatial_rtdose=load_spatial_rtdose,
            require_spatial_rtdose=load_spatial_rtdose,
        )
        target = prepare_stage8_evaluation_target(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=target_spacing,
            reference=inputs.observed,
        )

        observed_t2 = np.asarray(
            target.target.gtv.data > 0.5,
            dtype=bool,
        )
        persistence = np.asarray(
            inputs.observed.gtv.data > 0.5,
            dtype=bool,
        )
        prepared[patient_id] = _PreparedPatient(
            inputs=inputs,
            target=target,
            observed_t2=observed_t2,
            persistence=persistence,
            persistence_dice=dice_score(
                persistence,
                observed_t2,
            ),
            persistence_relative_volume_error=relative_volume_error(
                persistence,
                observed_t2,
            ),
            persistence_hd95_mm=hausdorff95_mm(
                persistence,
                observed_t2,
                spacing=target.target.spacing,
            ),
            persistence_centroid_distance_mm=centroid_distance_mm(
                persistence,
                observed_t2,
                spacing=target.target.spacing,
            ),
        )

    return prepared


def _mask_volume_cm3(
    mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
) -> float:
    voxel_volume_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    return float(np.count_nonzero(mask) * voxel_volume_mm3 / 1000.0)


def _evaluate_candidate(
    *,
    candidate: Stage9DelayedCandidate,
    patient_id: int,
    patient: _PreparedPatient,
    kinetics: FrozenStage8Kinetics,
    selected_stage8: SelectedStage8Model,
    observation: MRIDetectionObservationParameters,
    dt_days: float,
) -> Stage9PatientCandidateEvaluation:
    radiobiology = RadiobiologyParameters(
        alpha_per_gy=(
            selected_stage8.candidate.effective_alpha_per_gy
        ),
        alpha_beta_ratio_gy=(
            selected_stage8.candidate.alpha_beta_ratio_gy
        ),
    )
    delayed = DelayedResponseParameters(
        damage_transfer_fraction=candidate.damage_transfer_fraction,
        damage_half_life_days=candidate.damage_half_life_days,
        damaged_visibility=candidate.damaged_visibility,
    )
    forecast = simulate_stage9_forecast(
        inputs=patient.inputs,
        target_day=patient.target.target.days_from_baseline,
        growth=ReactionDiffusionParameters(
            diffusion=kinetics.diffusion,
            proliferation=kinetics.proliferation,
        ),
        radiobiology=radiobiology,
        proliferation_survival=(
            selected_stage8.candidate.proliferation_survival
        ),
        delayed=delayed,
        dt_days=dt_days,
        observation_parameters=observation,
    )
    predicted = forecast.prediction_mask

    twin_dice = dice_score(predicted, patient.observed_t2)
    t1_volume = _mask_volume_cm3(
        patient.persistence,
        spacing=patient.target.target.spacing,
    )
    t2_volume = _mask_volume_cm3(
        patient.observed_t2,
        spacing=patient.target.target.spacing,
    )
    predicted_volume = _mask_volume_cm3(
        predicted,
        spacing=patient.target.target.spacing,
    )
    volume_change = (
        0.0
        if t1_volume <= 0.0
        else (t2_volume - t1_volume) / t1_volume
    )
    last_fraction_day = max(patient.inputs.schedule.fraction_days)

    return Stage9PatientCandidateEvaluation(
        patient_id=patient_id,
        candidate_id=candidate.candidate_id,
        damage_transfer_fraction=candidate.damage_transfer_fraction,
        damage_half_life_days=candidate.damage_half_life_days,
        damaged_visibility=candidate.damaged_visibility,
        complexity_rank=candidate.complexity_rank,
        diffusion=kinetics.diffusion,
        proliferation=kinetics.proliferation,
        twin_dice=twin_dice,
        persistence_dice=patient.persistence_dice,
        delta_vs_persistence=twin_dice - patient.persistence_dice,
        relative_volume_error=relative_volume_error(
            predicted,
            patient.observed_t2,
        ),
        persistence_relative_volume_error=(
            patient.persistence_relative_volume_error
        ),
        hd95_mm=hausdorff95_mm(
            predicted,
            patient.observed_t2,
            spacing=patient.target.target.spacing,
        ),
        persistence_hd95_mm=patient.persistence_hd95_mm,
        centroid_distance_mm=centroid_distance_mm(
            predicted,
            patient.observed_t2,
            spacing=patient.target.target.spacing,
        ),
        persistence_centroid_distance_mm=(
            patient.persistence_centroid_distance_mm
        ),
        t1_day=patient.inputs.observed.days_from_baseline,
        t2_day=patient.target.target.days_from_baseline,
        forecast_horizon_days=(
            patient.target.target.days_from_baseline
            - patient.inputs.observed.days_from_baseline
        ),
        days_last_rt_to_t1=(
            patient.inputs.observed.days_from_baseline
            - last_fraction_day
        ),
        observed_t1_volume_cm3=t1_volume,
        observed_t2_volume_cm3=t2_volume,
        predicted_t2_volume_cm3=predicted_volume,
        observed_volume_change_fraction=volume_change,
    )


def _summary(
    rows: list[Stage9PatientCandidateEvaluation],
    *,
    catastrophic_threshold: float,
) -> Stage9CandidateSummary:
    if not rows:
        raise ValueError("Cannot summarize empty Stage 9 candidate rows")

    candidate_ids = {row.candidate_id for row in rows}
    if len(candidate_ids) != 1:
        raise ValueError("Stage 9 summary rows mix candidates")

    ranks = {row.complexity_rank for row in rows}
    if len(ranks) != 1:
        raise ValueError("Stage 9 candidate complexity is inconsistent")

    deltas = [row.delta_vs_persistence for row in rows]
    return Stage9CandidateSummary(
        candidate_id=rows[0].candidate_id,
        complexity_rank=ranks.pop(),
        patient_count=len(rows),
        mean_dice=float(fmean(row.twin_dice for row in rows)),
        median_dice=float(median(row.twin_dice for row in rows)),
        mean_delta_vs_persistence=float(fmean(deltas)),
        median_delta_vs_persistence=float(median(deltas)),
        mean_relative_volume_error=float(
            fmean(row.relative_volume_error for row in rows)
        ),
        mean_hd95_mm=_optional_mean([row.hd95_mm for row in rows]),
        catastrophic_failure_count=sum(
            value < catastrophic_threshold
            for value in deltas
        ),
        better_count=sum(value > 1e-6 for value in deltas),
        equal_count=sum(abs(value) <= 1e-6 for value in deltas),
        worse_count=sum(value < -1e-6 for value in deltas),
    )


def _phase_summaries(
    *,
    candidates: tuple[Stage9DelayedCandidate, ...],
    patient_ids: tuple[int, ...],
    evaluations: dict[
        tuple[int, str],
        Stage9PatientCandidateEvaluation,
    ],
    catastrophic_threshold: float,
) -> tuple[Stage9CandidateSummary, ...]:
    summaries: list[Stage9CandidateSummary] = []
    for candidate in candidates:
        rows = [
            evaluations[(patient_id, candidate.candidate_id)]
            for patient_id in patient_ids
        ]
        summaries.append(
            _summary(
                rows,
                catastrophic_threshold=catastrophic_threshold,
            )
        )
    return tuple(summaries)


def _select_summary(
    summaries: tuple[Stage9CandidateSummary, ...],
    *,
    control: Stage9CandidateSummary,
    config: Stage9ProtocolConfig,
) -> Stage9CandidateSummary:
    eligible: list[Stage9CandidateSummary] = []

    for summary in summaries:
        if summary.candidate_id == control.candidate_id:
            eligible.append(summary)
            continue

        mean_gain = summary.mean_dice - control.mean_dice
        allowed_catastrophic = (
            control.catastrophic_failure_count
            + config.selection.max_additional_catastrophic_failures
        )
        if (
            mean_gain
            >= config.selection.min_mean_dice_gain_over_stage8_control
            and summary.catastrophic_failure_count
            <= allowed_catastrophic
        ):
            eligible.append(summary)

    if not eligible:
        return control

    return min(
        eligible,
        key=lambda item: (
            -item.mean_dice,
            -item.median_dice,
            item.catastrophic_failure_count,
            (
                float("inf")
                if item.mean_hd95_mm is None
                else item.mean_hd95_mm
            ),
            item.complexity_rank,
            item.candidate_id,
        ),
    )


def _loo_counts(
    *,
    candidates: tuple[Stage9DelayedCandidate, ...],
    patient_ids: tuple[int, ...],
    evaluations: dict[
        tuple[int, str],
        Stage9PatientCandidateEvaluation,
    ],
    config: Stage9ProtocolConfig,
) -> dict[str, int]:
    counts: Counter[str] = Counter()

    for held_out in patient_ids:
        training = tuple(
            patient_id
            for patient_id in patient_ids
            if patient_id != held_out
        )
        summaries = _phase_summaries(
            candidates=candidates,
            patient_ids=training,
            evaluations=evaluations,
            catastrophic_threshold=(
                config.selection.catastrophic_delta_vs_persistence
            ),
        )
        control = next(
            summary
            for summary in summaries
            if summary.candidate_id == control_candidate().candidate_id
        )
        selected = _select_summary(
            summaries,
            control=control,
            config=config,
        )
        counts[selected.candidate_id] += 1

    return dict(sorted(counts.items()))


def _write_csv(
    path: Path,
    rows: list[Stage9PatientCandidateEvaluation],
) -> None:
    if not rows:
        return

    fieldnames = list(asdict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def select_stage9_delayed_response(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    stage9_protocol_path: Path,
    data_audit_root: Path,
    stage8_selection_root: Path,
    stage8_validation_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Stage9SelectionArtifact:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Stage 9 selection destination already exists: {destination}"
        )

    repository = read_repository_state(repo_root.resolve())
    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Stage 9 selection requires a clean Git working tree"
        )

    audit = load_sealed_stage8_data_audit(data_audit_root)
    audit_sha = sha256_file(
        data_audit_root.resolve() / "stage8_data_audit.json"
    )
    selected_stage8 = load_selected_stage8_model(
        stage8_selection_root
    )

    if selected_stage8.stage8_data_audit_sha256 != audit_sha:
        raise ValueError(
            "Stage 8 selection does not match the sealed data audit"
        )

    experiment_sha = sha256_file(experiment_config_path.resolve())
    stage8_protocol_sha = sha256_file(stage8_protocol_path.resolve())
    if selected_stage8.experiment_config_sha256 != experiment_sha:
        raise ValueError(
            "Stage 8 selection does not match experiment config"
        )
    if selected_stage8.protocol_config_sha256 != stage8_protocol_sha:
        raise ValueError(
            "Stage 8 selection does not match Stage 8 protocol"
        )

    (
        kinetics,
        _stage8_selection_manifest,
        _stage8_validation_manifest,
        stage8_selection_sha,
        stage8_validation_sha,
    ) = _stage8_frozen_kinetics(
        stage8_selection_root=stage8_selection_root,
        stage8_validation_root=stage8_validation_root,
        selected=selected_stage8,
    )
    development_ids, reserve_ids, holdout_ids = (
        _development_and_reserve_ids(
            audit.manifest,
            development_ids=set(kinetics),
        )
    )

    experiment = load_cohort_experiment_config(experiment_config_path)
    metadata_root = (
        experiment.metadata_root
        if experiment.metadata_root.is_absolute()
        else repo_root.resolve() / experiment.metadata_root
    )
    patients_root = (
        experiment.patients_root
        if experiment.patients_root.is_absolute()
        else repo_root.resolve() / experiment.patients_root
    )

    issues = preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=development_ids,
        require_spatial_rtdose=(
            selected_stage8.candidate.use_spatial_rtdose
        ),
    )
    if issues:
        preview = "\n".join(
            f"  patient {item.patient_id}: {item.input_name} -> "
            f"{item.expected_path}"
            for item in issues[:30]
        )
        raise FileNotFoundError(
            "Stage 9 development inputs are incomplete:\n" + preview
        )

    observation = _observation_parameters(stage8_protocol_path)
    treatment = CFBTreatmentMetadata(metadata_root)
    prepared = _prepare_patients(
        patient_ids=development_ids,
        metadata_root=metadata_root,
        patients_root=patients_root,
        target_spacing=experiment.evaluation.target_spacing,
        treatment=treatment,
        observation=observation,
        load_spatial_rtdose=(
            selected_stage8.candidate.use_spatial_rtdose
        ),
        progress=progress,
    )

    stage9 = load_stage9_protocol_config(stage9_protocol_path)
    control = control_candidate()
    evaluation_cache: dict[
        tuple[int, str],
        Stage9PatientCandidateEvaluation,
    ] = {}
    candidate_index: dict[str, Stage9DelayedCandidate] = {
        control.candidate_id: control
    }
    phases: list[dict[str, object]] = []

    def evaluate_candidates(
        candidates: tuple[Stage9DelayedCandidate, ...],
        *,
        phase_name: str,
    ) -> tuple[Stage9CandidateSummary, ...]:
        unique = deduplicate_candidates(candidates)
        candidate_index.update(
            (candidate.candidate_id, candidate)
            for candidate in unique
        )

        total = len(unique) * len(development_ids)
        job = 0
        for candidate in unique:
            for patient_id in development_ids:
                job += 1
                key = (patient_id, candidate.candidate_id)
                if key in evaluation_cache:
                    continue

                started = time.perf_counter()
                if progress is not None:
                    progress(
                        f"[stage9] {phase_name} {job}/{total}: "
                        f"patient={patient_id} "
                        f"candidate={candidate.candidate_id}"
                    )

                row = _evaluate_candidate(
                    candidate=candidate,
                    patient_id=patient_id,
                    patient=prepared[patient_id],
                    kinetics=kinetics[patient_id],
                    selected_stage8=selected_stage8,
                    observation=observation,
                    dt_days=experiment.evaluation.dt,
                )
                evaluation_cache[key] = row

                if (
                    candidate.candidate_id == control.candidate_id
                    and not math.isclose(
                        row.twin_dice,
                        kinetics[patient_id].expected_stage8_dice,
                        rel_tol=0.0,
                        abs_tol=1e-6,
                    )
                ):
                    raise RuntimeError(
                        "Stage 9 control does not reproduce sealed Stage 8 "
                        f"for patient {patient_id}: "
                        f"{row.twin_dice:.8f} vs "
                        f"{kinetics[patient_id].expected_stage8_dice:.8f}"
                    )

                if progress is not None:
                    progress(
                        f"[stage9]   done in "
                        f"{time.perf_counter() - started:.1f}s; "
                        f"Dice={row.twin_dice:.4f}; "
                        f"delta={row.delta_vs_persistence:+.4f}"
                    )

        return _phase_summaries(
            candidates=unique,
            patient_ids=development_ids,
            evaluations=evaluation_cache,
            catastrophic_threshold=(
                stage9.selection.catastrophic_delta_vs_persistence
            ),
        )

    phase1_candidates = timescale_candidates(
        stage9.delayed.half_life_days
    )
    phase1_summaries = evaluate_candidates(
        phase1_candidates,
        phase_name="timescale",
    )
    control_summary = next(
        summary
        for summary in phase1_summaries
        if summary.candidate_id == control.candidate_id
    )
    phase1_selected = _select_summary(
        phase1_summaries,
        control=control_summary,
        config=stage9,
    )
    phases.append(
        {
            "name": "timescale",
            "selected_candidate_id": phase1_selected.candidate_id,
            "summaries": [asdict(item) for item in phase1_summaries],
            "loo_selection_counts": _loo_counts(
                candidates=deduplicate_candidates(phase1_candidates),
                patient_ids=development_ids,
                evaluations=evaluation_cache,
                config=stage9,
            ),
        }
    )

    final_summary = phase1_selected
    if phase1_selected.candidate_id != control.candidate_id:
        incumbent = candidate_index[phase1_selected.candidate_id]
        phase2_candidates = deduplicate_candidates(
            (
                control,
                *transfer_candidates(
                    half_life_days=incumbent.damage_half_life_days,
                    transfer_values=stage9.delayed.transfer_fractions,
                ),
            )
        )
        phase2_summaries = evaluate_candidates(
            phase2_candidates,
            phase_name="damage-transfer",
        )
        phase2_selected = _select_summary(
            phase2_summaries,
            control=control_summary,
            config=stage9,
        )
        phases.append(
            {
                "name": "damage-transfer",
                "selected_candidate_id": phase2_selected.candidate_id,
                "summaries": [asdict(item) for item in phase2_summaries],
                "loo_selection_counts": _loo_counts(
                    candidates=phase2_candidates,
                    patient_ids=development_ids,
                    evaluations=evaluation_cache,
                    config=stage9,
                ),
            }
        )
        final_summary = phase2_selected

        if phase2_selected.candidate_id != control.candidate_id:
            incumbent = candidate_index[phase2_selected.candidate_id]
            phase3_candidates = deduplicate_candidates(
                (
                    control,
                    *visibility_candidates(
                        half_life_days=incumbent.damage_half_life_days,
                        damage_transfer_fraction=(
                            incumbent.damage_transfer_fraction
                        ),
                        visibility_values=(
                            stage9.delayed.visibility_values
                        ),
                    ),
                )
            )
            phase3_summaries = evaluate_candidates(
                phase3_candidates,
                phase_name="damaged-visibility",
            )
            phase3_selected = _select_summary(
                phase3_summaries,
                control=control_summary,
                config=stage9,
            )
            phases.append(
                {
                    "name": "damaged-visibility",
                    "selected_candidate_id": (
                        phase3_selected.candidate_id
                    ),
                    "summaries": [
                        asdict(item) for item in phase3_summaries
                    ],
                    "loo_selection_counts": _loo_counts(
                        candidates=phase3_candidates,
                        patient_ids=development_ids,
                        evaluations=evaluation_cache,
                        config=stage9,
                    ),
                }
            )
            final_summary = phase3_selected

    selected_candidate = candidate_index[final_summary.candidate_id]
    all_rows = sorted(
        evaluation_cache.values(),
        key=lambda item: (item.candidate_id, item.patient_id),
    )
    selected_rows = [
        evaluation_cache[(patient_id, selected_candidate.candidate_id)]
        for patient_id in development_ids
    ]

    payload: dict[str, object] = {
        "schema_version": STAGE9_SELECTION_SCHEMA_VERSION,
        "kind": "stage9_delayed_response_development_selection",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "stage8_model_selection_sha256": stage8_selection_sha,
            "stage8_internal_validation_sha256": stage8_validation_sha,
            "stage8_protocol_sha256": stage8_protocol_sha,
            "stage9_protocol_sha256": sha256_file(
                stage9_protocol_path.resolve()
            ),
            "experiment_config_sha256": experiment_sha,
        },
        "leakage_control": {
            "development_patient_ids": list(development_ids),
            "reserve_patient_ids": list(reserve_ids),
            "untouched_holdout_patient_ids": list(holdout_ids),
            "stage8_internal_validation_is_now_development_exposed": True,
            "reserve_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "patient_specific_kinetics_refit": False,
        },
        "design": {
            "name": STAGE9_SELECTION_DESIGN,
            "frozen_patient_specific_parameters": ["D", "rho"],
            "global_candidate_parameters": [
                "damage_transfer_fraction",
                "damage_half_life_days",
                "damaged_visibility",
            ],
            "phase_order": [
                phase["name"]
                for phase in phases
            ],
            "guardrails": asdict(stage9.selection),
        },
        "stage8_control": asdict(control_summary),
        "selected_candidate": asdict(selected_candidate),
        "selected_summary": asdict(final_summary),
        "phases": phases,
        "patient_candidate_results": [
            asdict(item)
            for item in all_rows
        ],
        "selected_patient_results": [
            asdict(item)
            for item in selected_rows
        ],
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )
    try:
        manifest_path = temporary / "stage9_delayed_selection.json"
        manifest_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (temporary / "stage9_delayed_selection.sha256").write_text(
            sha256_file(manifest_path)
            + "  stage9_delayed_selection.json\n",
            encoding="ascii",
        )
        _write_csv(
            temporary / "stage9_delayed_selection.csv",
            all_rows,
        )
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return Stage9SelectionArtifact(
        directory=destination,
        manifest=payload,
    )
