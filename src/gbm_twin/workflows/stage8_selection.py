from __future__ import annotations

import csv
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from gbm_twin.calibration.stage8 import (
    Stage8CalibrationConfig,
    calibrate_stage8_interval,
)
from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.evaluation.stage8_model_selection import (
    Stage8PatientCandidateScore,
    select_stage8_model,
)
from gbm_twin.models.observation import (
    MRIDetectionObservationParameters,
    latent_density_from_mri_detection,
)
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.rt_schedule import reconstruct_weekday_like_schedule
from gbm_twin.models.treatment_memory import initial_treatment_memory_state
from gbm_twin.workflows.patients import prepare_patient_timepoint
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_forecast import simulate_stage8_forecast
from gbm_twin.workflows.stage8_inputs import prepare_spatial_rtdose
from gbm_twin.workflows.stage8_model_family import (
    Stage8ModelCandidate,
    build_stage8_model_family,
)
from gbm_twin.workflows.stage8_protocol import (
    Stage8ProtocolConfig,
    load_stage8_protocol_config,
)
from gbm_twin.workflows.stage8_treatment import (
    build_stage8_radiotherapy_events,
)

STAGE8_SELECTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Stage8PatientCandidateEvaluation:
    patient_id: int
    candidate_id: str
    use_spatial_rtdose: bool
    effective_alpha_per_gy: float
    alpha_beta_ratio_gy: float
    proliferation_survival: float
    diffusion: float
    proliferation: float
    calibration_dice: float
    calibration_volume_error: float
    calibration_loss: float
    calibration_identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool
    t2_dice: float
    t2_relative_volume_error: float
    t2_hd95_mm: float | None
    t2_centroid_distance_mm: float | None


@dataclass(frozen=True)
class Stage8CandidateFailure:
    patient_id: int
    candidate_id: str
    reason: str


@dataclass(frozen=True)
class Stage8SelectionArtifact:
    directory: Path
    manifest: dict[str, object]


def _audit_development_ids(audit: dict[str, object]) -> tuple[int, ...]:
    raw_patients = audit.get("patients")

    if not isinstance(raw_patients, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    selected: list[int] = []

    for raw in raw_patients:
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")

        if raw.get("split") != "development-exposed":
            continue

        if raw.get("core_eligible") is not True:
            continue

        patient_id = raw.get("patient_id")

        if type(patient_id) is not int:
            raise ValueError("Stage 8 audit patient_id must be an integer")

        selected.append(patient_id)

    result = tuple(sorted(selected))

    if len(result) < 3:
        raise ValueError(
            "Stage 8 model selection needs at least 3 eligible "
            "development-exposed patients"
        )

    return result


def _candidate_by_id(
    candidates: tuple[Stage8ModelCandidate, ...],
) -> dict[str, Stage8ModelCandidate]:
    result = {candidate.candidate_id: candidate for candidate in candidates}

    if len(result) != len(candidates):
        raise ValueError("Stage 8 model family contains duplicate IDs")

    return result


def _observation_parameters(
    protocol: Stage8ProtocolConfig,
) -> MRIDetectionObservationParameters:
    return MRIDetectionObservationParameters(
        enhancing_threshold=(
            protocol.observation.enhancing_detection_threshold
        ),
        infiltrative_threshold=(
            protocol.observation.infiltrative_detection_threshold
        ),
        transition_width_mm=(
            protocol.observation.transition_width_mm
        ),
    )


def _calibration_config(
    *,
    protocol: Stage8ProtocolConfig,
    experiment_path: Path,
) -> Stage8CalibrationConfig:
    experiment = load_cohort_experiment_config(experiment_path)
    evaluation = experiment.evaluation

    return Stage8CalibrationConfig(
        diffusion_values=evaluation.diffusion_values,
        proliferation_values=evaluation.proliferation_values,
        dt_days=evaluation.dt,
        observation_threshold=(
            protocol.observation.enhancing_detection_threshold
        ),
        soft_temperature=0.05,
        volume_weight=evaluation.volume_weight,
        refinement_rounds=evaluation.refinement_rounds,
        upper_boundary_expansion_factor=(
            evaluation.upper_boundary_expansion_factor
        ),
    )


def _treatment_schedule(
    treatment: CFBTreatmentMetadata,
    patient_id: int,
):
    record = treatment.treatment(patient_id)

    if (
        record is None
        or record.radiotherapy_start_day is None
        or record.dose_gy is None
        or record.fractions_number is None
    ):
        raise ValueError(
            f"Patient {patient_id}: complete RT schedule is required"
        )

    return reconstruct_weekday_like_schedule(
        start_day=record.radiotherapy_start_day,
        total_dose_gy=record.dose_gy,
        fractions_number=record.fractions_number,
    )


def _calibration_events(
    events,
    *,
    start_day: float,
    end_day: float,
):
    tolerance = 1e-9
    return tuple(
        event
        for event in events
        if event.day >= start_day - tolerance
        and event.day <= end_day + tolerance
    )


def _evaluate_candidate_patient(
    *,
    patient_id: int,
    candidate: Stage8ModelCandidate,
    metadata_root: Path,
    patients_root: Path,
    target_spacing: tuple[float, float, float],
    treatment: CFBTreatmentMetadata,
    observation_parameters: MRIDetectionObservationParameters,
    calibration_config: Stage8CalibrationConfig,
    cache_root: Path,
    workers: int,
) -> Stage8PatientCandidateEvaluation:
    start = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t0",
        target_spacing=target_spacing,
    )
    observed = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t1",
        target_spacing=target_spacing,
    )
    target = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t2",
        target_spacing=target_spacing,
    )

    schedule = _treatment_schedule(treatment, patient_id)
    radiobiology = RadiobiologyParameters(
        alpha_per_gy=candidate.effective_alpha_per_gy,
        alpha_beta_ratio_gy=candidate.alpha_beta_ratio_gy,
    )

    cumulative_rtdose: np.ndarray | None = None

    if candidate.use_spatial_rtdose:
        prepared_dose = prepare_spatial_rtdose(
            patients_root=patients_root,
            patient_id=patient_id,
            reference=start.t1gd,
        )

        if prepared_dose is None:
            raise FileNotFoundError(
                f"Patient {patient_id}: spatial candidate requires local RTDOSE"
            )

        cumulative_rtdose = np.asarray(
            prepared_dose.volume.data,
            dtype=np.float32,
        )

    domain = np.asarray(
        (start.brain_mask.data > 0.5)
        | (observed.brain_mask.data > 0.5)
        | (start.gtv.data > 0.5)
        | (observed.gtv.data > 0.5),
        dtype=bool,
    )
    initial_density = latent_density_from_mri_detection(
        start.gtv.data > 0.5,
        domain,
        spacing=start.spacing,
        parameters=observation_parameters,
    )
    initial_state = initial_treatment_memory_state(
        initial_density,
        domain_mask=domain,
    )
    rt_events = build_stage8_radiotherapy_events(
        schedule,
        radiobiology,
        proliferation_survival=candidate.proliferation_survival,
        cumulative_rtdose=cumulative_rtdose,
    )
    calibration = calibrate_stage8_interval(
        initial_state=initial_state,
        observed_mask=observed.gtv.data > 0.5,
        domain_mask=domain,
        spacing=start.spacing,
        duration_days=(
            observed.days_from_baseline - start.days_from_baseline
        ),
        fraction_events=_calibration_events(
            rt_events.events,
            start_day=start.days_from_baseline,
            end_day=observed.days_from_baseline,
        ),
        config=calibration_config,
        cache_dir=(
            cache_root
            / f"patient-{patient_id}"
            / candidate.candidate_id
        ),
        workers=workers,
    )
    forecast = simulate_stage8_forecast(
        start=start,
        observed=observed,
        target_day=target.days_from_baseline,
        parameters=ReactionDiffusionParameters(
            diffusion=calibration.best.diffusion,
            proliferation=calibration.best.proliferation,
        ),
        schedule=schedule,
        radiobiology=radiobiology,
        proliferation_survival=candidate.proliferation_survival,
        dt_days=calibration_config.dt_days,
        observation_parameters=observation_parameters,
        cumulative_rtdose=cumulative_rtdose,
    )
    observed_t2 = np.asarray(target.gtv.data > 0.5, dtype=bool)
    predicted_t2 = forecast.prediction_mask

    return Stage8PatientCandidateEvaluation(
        patient_id=patient_id,
        candidate_id=candidate.candidate_id,
        use_spatial_rtdose=candidate.use_spatial_rtdose,
        effective_alpha_per_gy=candidate.effective_alpha_per_gy,
        alpha_beta_ratio_gy=candidate.alpha_beta_ratio_gy,
        proliferation_survival=candidate.proliferation_survival,
        diffusion=calibration.best.diffusion,
        proliferation=calibration.best.proliferation,
        calibration_dice=calibration.best.dice,
        calibration_volume_error=calibration.best.volume_error,
        calibration_loss=calibration.best.loss,
        calibration_identifiable=calibration.diagnostics.identifiable,
        diffusion_at_boundary=(
            calibration.diagnostics.diffusion_at_boundary
        ),
        proliferation_at_boundary=(
            calibration.diagnostics.proliferation_at_boundary
        ),
        t2_dice=dice_score(predicted_t2, observed_t2),
        t2_relative_volume_error=relative_volume_error(
            predicted_t2,
            observed_t2,
        ),
        t2_hd95_mm=hausdorff95_mm(
            predicted_t2,
            observed_t2,
            spacing=target.spacing,
        ),
        t2_centroid_distance_mm=centroid_distance_mm(
            predicted_t2,
            observed_t2,
            spacing=target.spacing,
        ),
    )


def _write_csv(
    path: Path,
    rows: list[Stage8PatientCandidateEvaluation],
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


def select_stage8_model_family(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    protocol_config_path: Path,
    data_audit_root: Path,
    cache_root: Path,
    output_dir: Path,
    workers: int = 1,
    allow_dirty: bool = False,
) -> Stage8SelectionArtifact:
    destination = output_dir.resolve()

    if destination.exists():
        raise FileExistsError(
            f"Stage 8 model-selection destination already exists: {destination}"
        )

    repository = read_repository_state(repo_root.resolve())

    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Stage 8 model selection requires a clean Git working tree"
        )

    experiment = load_cohort_experiment_config(experiment_config_path)
    protocol = load_stage8_protocol_config(protocol_config_path)
    audit = load_sealed_stage8_data_audit(data_audit_root)

    expected_protocol_sha = audit.manifest.get("protocol_config_sha256")
    actual_protocol_sha = sha256_file(protocol_config_path.resolve())

    if expected_protocol_sha != actual_protocol_sha:
        raise ValueError(
            "Stage 8 audit does not match the current protocol config"
        )

    development_ids = _audit_development_ids(audit.manifest)
    observation_parameters = _observation_parameters(protocol)
    calibration_config = _calibration_config(
        protocol=protocol,
        experiment_path=experiment_config_path,
    )
    candidates = build_stage8_model_family(protocol)
    candidate_index = _candidate_by_id(candidates)
    metadata_root = (
        experiment.metadata_root
        if experiment.metadata_root.is_absolute()
        else repo_root / experiment.metadata_root
    )
    patients_root = (
        experiment.patients_root
        if experiment.patients_root.is_absolute()
        else repo_root / experiment.patients_root
    )
    treatment = CFBTreatmentMetadata(metadata_root)
    rows: list[Stage8PatientCandidateEvaluation] = []
    failures: list[Stage8CandidateFailure] = []

    for candidate in candidates:
        for patient_id in development_ids:
            try:
                row = _evaluate_candidate_patient(
                    patient_id=patient_id,
                    candidate=candidate,
                    metadata_root=metadata_root,
                    patients_root=patients_root,
                    target_spacing=experiment.evaluation.target_spacing,
                    treatment=treatment,
                    observation_parameters=observation_parameters,
                    calibration_config=calibration_config,
                    cache_root=cache_root.resolve(),
                    workers=workers,
                )
            except (FileNotFoundError, ValueError) as exc:
                failures.append(
                    Stage8CandidateFailure(
                        patient_id=patient_id,
                        candidate_id=candidate.candidate_id,
                        reason=str(exc),
                    )
                )
                continue

            rows.append(row)

    scores = tuple(
        Stage8PatientCandidateScore(
            patient_id=row.patient_id,
            candidate_id=row.candidate_id,
            complexity_rank=candidate_index[row.candidate_id].complexity_rank,
            dice=row.t2_dice,
            relative_volume_error=row.t2_relative_volume_error,
            hd95_mm=row.t2_hd95_mm,
            centroid_distance_mm=row.t2_centroid_distance_mm,
        )
        for row in rows
    )
    selection = select_stage8_model(
        scores,
        development_patient_ids=development_ids,
    )
    selected_candidate = candidate_index[
        selection.selected_candidate_id
    ]

    payload: dict[str, object] = {
        "schema_version": STAGE8_SELECTION_SCHEMA_VERSION,
        "kind": "stage8_development_model_selection",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "source": {
            "stage8_data_audit_sha256": sha256_file(
                data_audit_root.resolve() / "stage8_data_audit.json"
            ),
            "protocol_config_sha256": actual_protocol_sha,
            "experiment_config_sha256": sha256_file(
                experiment_config_path.resolve()
            ),
        },
        "leakage_control": {
            "development_t2_loaded": True,
            "development_patient_ids": list(development_ids),
            "untouched_holdout_t2_loaded": False,
            "candidate_selection_uses_only_development_exposed": True,
        },
        "selection_rule": {
            "candidate_ranking": [
                "mean_t2_dice_desc",
                "median_t2_dice_desc",
                "mean_relative_volume_error_asc",
                "complexity_rank_asc",
                "candidate_id_asc",
            ],
            "internal_validation": "leave_one_patient_out",
        },
        "selected_candidate": asdict(selected_candidate),
        "loo": {
            "mean_dice": selection.loo_mean_dice,
            "median_dice": selection.loo_median_dice,
            "mean_relative_volume_error": (
                selection.loo_mean_relative_volume_error
            ),
            "selection_counts": selection.loo_selection_counts,
            "folds": [asdict(fold) for fold in selection.loo_folds],
        },
        "candidate_summaries": [
            asdict(summary)
            for summary in selection.candidate_summaries
        ],
        "patient_candidate_evaluations": [
            asdict(row) for row in rows
        ],
        "candidate_failures": [
            asdict(failure) for failure in failures
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
        manifest_path = temporary / "stage8_model_selection.json"
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
        (temporary / "stage8_model_selection.sha256").write_text(
            sha256_file(manifest_path) + "  stage8_model_selection.json\n",
            encoding="ascii",
        )
        _write_csv(temporary / "stage8_model_selection.csv", rows)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return Stage8SelectionArtifact(
        directory=destination,
        manifest=payload,
    )
