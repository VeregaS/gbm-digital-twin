from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, median

import numpy as np

from gbm_twin.calibration.stage8 import Stage8CalibrationConfig
from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_candidate import evaluate_stage8_candidate
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_inputs import discover_patient_rtdose_path
from gbm_twin.workflows.stage8_patient import (
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_protocol import load_stage8_protocol_config
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)

STAGE8_VALIDATION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Stage8InternalValidationRow:
    patient_id: int
    twin_dice: float
    persistence_dice: float
    twin_minus_persistence_dice: float
    twin_relative_volume_error: float
    persistence_relative_volume_error: float
    twin_hd95_mm: float | None
    persistence_hd95_mm: float | None
    twin_centroid_distance_mm: float | None
    persistence_centroid_distance_mm: float | None
    diffusion: float
    proliferation: float
    calibration_dice: float
    calibration_loss: float
    calibration_identifiable: bool


@dataclass(frozen=True)
class Stage8ValidationArtifact:
    directory: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class Stage8MaterializationIssue:
    patient_id: int
    input_name: str
    expected_path: str


def _required_timepoint_paths(
    patients_root: Path,
    *,
    patient_id: int,
    timepoint: str,
) -> tuple[tuple[str, Path], ...]:
    directory = patients_root / str(patient_id) / timepoint
    prefix = f"{patient_id}_{timepoint}"
    return (
        ("T1Gd", directory / f"{prefix}_t1gd.nii.gz"),
        ("GTV", directory / f"{prefix}_gtv.nii.gz"),
        ("brain mask", directory / f"{prefix}_brain_mask.nii.gz"),
    )


def preflight_stage8_validation_inputs(
    *,
    patients_root: Path,
    patient_ids: tuple[int, ...],
    require_spatial_rtdose: bool,
) -> tuple[Stage8MaterializationIssue, ...]:
    """Check local files without loading any validation image content."""

    issues: list[Stage8MaterializationIssue] = []

    for patient_id in patient_ids:
        for timepoint in ("t0", "t1", "t2"):
            for input_name, path in _required_timepoint_paths(
                patients_root,
                patient_id=patient_id,
                timepoint=timepoint,
            ):
                if not path.is_file():
                    issues.append(
                        Stage8MaterializationIssue(
                            patient_id=patient_id,
                            input_name=f"{timepoint} {input_name}",
                            expected_path=str(path),
                        )
                    )

        if require_spatial_rtdose:
            try:
                rtdose = discover_patient_rtdose_path(
                    patients_root=patients_root,
                    patient_id=patient_id,
                )
            except ValueError as exc:
                issues.append(
                    Stage8MaterializationIssue(
                        patient_id=patient_id,
                        input_name="RTDOSE",
                        expected_path=str(exc),
                    )
                )
            else:
                if rtdose is None:
                    issues.append(
                        Stage8MaterializationIssue(
                            patient_id=patient_id,
                            input_name="RTDOSE",
                            expected_path=(
                                str(patients_root / str(patient_id))
                                + r"\**\*rtdose*.nii.gz"
                            ),
                        )
                    )

    return tuple(issues)


def _materialization_error(
    issues: tuple[Stage8MaterializationIssue, ...],
) -> str:
    patient_count = len({issue.patient_id for issue in issues})
    preview_limit = 40
    lines = [
        (
            "Stage 8 internal validation preflight failed before any t2 "
            "image content was loaded."
        ),
        (
            f"Missing or ambiguous local inputs: {len(issues)} files/inputs "
            f"across {patient_count} patients."
        ),
        (
            "Materialize the sealed internal-validation cohort; do not drop "
            "or replace patients after model selection."
        ),
    ]

    for issue in issues[:preview_limit]:
        lines.append(
            f"  patient {issue.patient_id}: {issue.input_name} -> "
            f"{issue.expected_path}"
        )

    remaining = len(issues) - preview_limit
    if remaining > 0:
        lines.append(f"  ... and {remaining} more missing inputs")

    return "\n".join(lines)


def _validation_patient_ids(manifest: dict[str, object]) -> tuple[int, ...]:
    raw_patients = manifest.get("patients")
    if not isinstance(raw_patients, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    selected: list[int] = []
    for raw in raw_patients:
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")
        # schema v1 used `development` for previously untouched non-holdout
        # cases. `internal-validation` is accepted for the next audit schema.
        if raw.get("split") not in {"development", "internal-validation"}:
            continue
        if raw.get("core_eligible") is not True:
            continue
        if raw.get("exposed_development") is True:
            continue
        patient_id = raw.get("patient_id")
        if type(patient_id) is not int:
            raise ValueError("Stage 8 audit patient_id must be an integer")
        selected.append(patient_id)

    result = tuple(sorted(selected))
    if not result:
        raise ValueError("Stage 8 audit contains no internal-validation patients")
    return result


def _observation_parameters(protocol_path: Path) -> MRIDetectionObservationParameters:
    protocol = load_stage8_protocol_config(protocol_path)
    return MRIDetectionObservationParameters(
        enhancing_threshold=(
            protocol.observation.enhancing_detection_threshold
        ),
        infiltrative_threshold=(
            protocol.observation.infiltrative_detection_threshold
        ),
        transition_width_mm=protocol.observation.transition_width_mm,
    )


def _calibration_config(
    *,
    protocol_path: Path,
    experiment_path: Path,
) -> Stage8CalibrationConfig:
    protocol = load_stage8_protocol_config(protocol_path)
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


def _optional_mean(values: list[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return float(fmean(available)) if available else None


def _patient_progress_callback(
    progress: Callable[[str], None] | None,
    *,
    patient_id: int,
) -> Callable[[str], None]:
    def emit(message: str) -> None:
        if progress is not None:
            progress(
                f"[stage8-validation]   patient={patient_id}: {message}"
            )

    return emit


def _write_csv(path: Path, rows: list[Stage8InternalValidationRow]) -> None:
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


def validate_selected_stage8_model(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    protocol_config_path: Path,
    data_audit_root: Path,
    selection_root: Path,
    cache_root: Path,
    output_dir: Path,
    workers: int = 1,
    allow_dirty: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Stage8ValidationArtifact:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Stage 8 validation destination already exists: {destination}"
        )
    if workers < 1:
        raise ValueError("workers must be at least 1")

    repository = read_repository_state(repo_root.resolve())
    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Stage 8 internal validation requires a clean Git working tree"
        )

    audit = load_sealed_stage8_data_audit(data_audit_root)
    selected = load_selected_stage8_model(selection_root)
    audit_sha = sha256_file(
        data_audit_root.resolve() / "stage8_data_audit.json"
    )
    protocol_sha = sha256_file(protocol_config_path.resolve())
    experiment_sha = sha256_file(experiment_config_path.resolve())

    if selected.stage8_data_audit_sha256 != audit_sha:
        raise ValueError("Selected Stage 8 model does not match the data audit")
    if selected.protocol_config_sha256 != protocol_sha:
        raise ValueError("Selected Stage 8 model does not match the protocol config")
    if selected.experiment_config_sha256 != experiment_sha:
        raise ValueError(
            "Selected Stage 8 model does not match the experiment config"
        )

    patient_ids = _validation_patient_ids(audit.manifest)
    experiment = load_cohort_experiment_config(experiment_config_path)
    observation = _observation_parameters(protocol_config_path)
    calibration = _calibration_config(
        protocol_path=protocol_config_path,
        experiment_path=experiment_config_path,
    )
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

    if progress is not None:
        progress(
            f"[stage8-validation] preflight: {len(patient_ids)} sealed "
            "internal-validation patients"
        )

    materialization_issues = preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=patient_ids,
        require_spatial_rtdose=selected.candidate.use_spatial_rtdose,
    )
    if materialization_issues:
        raise FileNotFoundError(
            _materialization_error(materialization_issues)
        )

    if progress is not None:
        progress(
            "[stage8-validation] preflight passed; validation t2 reveal "
            "may begin"
        )

    rows: list[Stage8InternalValidationRow] = []
    total_patients = len(patient_ids)

    for patient_index, patient_id in enumerate(patient_ids, start=1):
        if progress is not None:
            progress(
                f"[stage8-validation] patient {patient_id} "
                f"({patient_index}/{total_patients}) starting"
            )

        started = time.perf_counter()
        inputs = prepare_stage8_forecast_inputs(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=experiment.evaluation.target_spacing,
            treatment=treatment,
            observation_parameters=observation,
            load_spatial_rtdose=selected.candidate.use_spatial_rtdose,
        )
        target = prepare_stage8_evaluation_target(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=experiment.evaluation.target_spacing,
            reference=inputs.observed,
        )
        calibration_progress = _patient_progress_callback(
            progress,
            patient_id=patient_id,
        )

        evaluation = evaluate_stage8_candidate(
            inputs=inputs,
            target=target,
            candidate=selected.candidate,
            observation_parameters=observation,
            calibration_config=calibration,
            cache_root=cache_root.resolve(),
            workers=workers,
            progress=calibration_progress,
        )

        observed_t2 = np.asarray(target.target.gtv.data > 0.5, dtype=bool)
        persistence = np.asarray(inputs.observed.gtv.data > 0.5, dtype=bool)
        persistence_dice = dice_score(persistence, observed_t2)
        persistence_volume_error = relative_volume_error(
            persistence,
            observed_t2,
        )
        persistence_hd95 = hausdorff95_mm(
            persistence,
            observed_t2,
            spacing=target.target.spacing,
        )
        persistence_centroid = centroid_distance_mm(
            persistence,
            observed_t2,
            spacing=target.target.spacing,
        )

        rows.append(
            Stage8InternalValidationRow(
                patient_id=patient_id,
                twin_dice=evaluation.t2_dice,
                persistence_dice=persistence_dice,
                twin_minus_persistence_dice=(
                    evaluation.t2_dice - persistence_dice
                ),
                twin_relative_volume_error=(
                    evaluation.t2_relative_volume_error
                ),
                persistence_relative_volume_error=(
                    persistence_volume_error
                ),
                twin_hd95_mm=evaluation.t2_hd95_mm,
                persistence_hd95_mm=persistence_hd95,
                twin_centroid_distance_mm=(
                    evaluation.t2_centroid_distance_mm
                ),
                persistence_centroid_distance_mm=persistence_centroid,
                diffusion=evaluation.diffusion,
                proliferation=evaluation.proliferation,
                calibration_dice=evaluation.calibration_dice,
                calibration_loss=evaluation.calibration_loss,
                calibration_identifiable=(
                    evaluation.calibration_identifiable
                ),
            )
        )

        if progress is not None:
            progress(
                f"[stage8-validation] patient {patient_id} done in "
                f"{time.perf_counter() - started:.1f}s; "
                f"Twin Dice={evaluation.t2_dice:.4f}; "
                f"Persistence Dice={persistence_dice:.4f}; "
                f"delta={evaluation.t2_dice - persistence_dice:+.4f}"
            )

    twin_dice = [row.twin_dice for row in rows]
    persistence_dice = [row.persistence_dice for row in rows]
    deltas = [row.twin_minus_persistence_dice for row in rows]
    payload: dict[str, object] = {
        "schema_version": STAGE8_VALIDATION_SCHEMA_VERSION,
        "kind": "stage8_internal_validation",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "stage8_model_selection_sha256": (
                selected.source_manifest_sha256
            ),
            "protocol_config_sha256": protocol_sha,
            "experiment_config_sha256": experiment_sha,
        },
        "selected_candidate": selected.provenance_payload(),
        "leakage_control": {
            "model_selection_changed": False,
            "development_exposed_t2_reloaded_for_selection": False,
            "internal_validation_t2_loaded": True,
            "internal_validation_patient_ids": list(patient_ids),
            "untouched_holdout_t2_loaded": False,
        },
        "summary": {
            "patient_count": len(rows),
            "mean_twin_dice": float(fmean(twin_dice)),
            "median_twin_dice": float(median(twin_dice)),
            "mean_persistence_dice": float(fmean(persistence_dice)),
            "mean_delta_vs_persistence": float(fmean(deltas)),
            "median_delta_vs_persistence": float(median(deltas)),
            "twin_better_than_persistence_count": sum(
                delta > 1e-6 for delta in deltas
            ),
            "twin_equal_to_persistence_count": sum(
                abs(delta) <= 1e-6 for delta in deltas
            ),
            "twin_worse_than_persistence_count": sum(
                delta < -1e-6 for delta in deltas
            ),
            "mean_twin_hd95_mm": _optional_mean(
                [row.twin_hd95_mm for row in rows]
            ),
            "mean_persistence_hd95_mm": _optional_mean(
                [row.persistence_hd95_mm for row in rows]
            ),
            "mean_twin_centroid_distance_mm": _optional_mean(
                [row.twin_centroid_distance_mm for row in rows]
            ),
            "mean_persistence_centroid_distance_mm": _optional_mean(
                [row.persistence_centroid_distance_mm for row in rows]
            ),
        },
        "patients": [asdict(row) for row in rows],
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )
    try:
        manifest_path = temporary / "stage8_internal_validation.json"
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
        (temporary / "stage8_internal_validation.sha256").write_text(
            sha256_file(manifest_path)
            + "  stage8_internal_validation.json\n",
            encoding="ascii",
        )
        _write_csv(temporary / "stage8_internal_validation.csv", rows)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return Stage8ValidationArtifact(
        directory=destination,
        manifest=payload,
    )
