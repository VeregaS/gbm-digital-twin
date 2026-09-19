from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, median

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
from gbm_twin.models.delayed_response import DelayedResponseParameters
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.treatment_memory import FractionResponseEvent
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_patient import (
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_protocol import load_stage8_protocol_config
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage8_treatment import build_stage8_radiotherapy_events
from gbm_twin.workflows.stage8_validation import (
    preflight_stage8_validation_inputs,
)
from gbm_twin.workflows.stage9_forecast import simulate_stage9_forecast
from gbm_twin.workflows.stage9_selection_artifact import (
    load_selected_stage9_model,
)
from gbm_twin.workflows.stage9_validation_plan import (
    load_stage9_validation_plan,
)

STAGE9_VALIDATION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Stage9ValidationRow:
    patient_id: int
    diffusion: float
    proliferation: float
    calibration_dice: float
    calibration_loss: float
    calibration_identifiable: bool
    twin_dice: float
    persistence_dice: float
    delta_vs_persistence: float
    twin_relative_volume_error: float
    persistence_relative_volume_error: float
    twin_hd95_mm: float | None
    persistence_hd95_mm: float | None
    twin_centroid_distance_mm: float | None
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
class Stage9ValidationArtifact:
    directory: Path
    manifest: dict[str, object]


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


def _calibration_config(
    *,
    stage8_protocol_path: Path,
    experiment_config_path: Path,
) -> Stage8CalibrationConfig:
    protocol = load_stage8_protocol_config(stage8_protocol_path)
    experiment = load_cohort_experiment_config(experiment_config_path)
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


def _events_for_interval(
    events: tuple[FractionResponseEvent, ...],
    *,
    start_day: float,
    end_day: float,
) -> tuple[FractionResponseEvent, ...]:
    tolerance = 1e-9
    return tuple(
        event
        for event in events
        if event.day >= start_day - tolerance
        and event.day <= end_day + tolerance
    )


def _mask_volume_cm3(
    mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
) -> float:
    voxel_volume_mm3 = float(np.prod(np.asarray(spacing, dtype=float)))
    return float(np.count_nonzero(mask) * voxel_volume_mm3 / 1000.0)


def _optional_mean(values: list[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return float(fmean(available)) if available else None


def _trajectory_group(
    volume_change_fraction: float,
    *,
    stable_threshold: float = 0.10,
) -> str:
    if volume_change_fraction > stable_threshold:
        return "growth"
    if volume_change_fraction < -stable_threshold:
        return "regression"
    return "stable"


def _trajectory_summary(
    rows: list[Stage9ValidationRow],
) -> dict[str, object]:
    result: dict[str, object] = {}

    for name in ("growth", "stable", "regression"):
        group = [
            row
            for row in rows
            if _trajectory_group(
                row.observed_volume_change_fraction
            )
            == name
        ]
        if not group:
            result[name] = {"patient_count": 0}
            continue

        result[name] = {
            "patient_count": len(group),
            "patient_ids": sorted(row.patient_id for row in group),
            "mean_dice": float(fmean(row.twin_dice for row in group)),
            "mean_delta_vs_persistence": float(
                fmean(row.delta_vs_persistence for row in group)
            ),
            "mean_hd95_mm": _optional_mean(
                [row.twin_hd95_mm for row in group]
            ),
            "mean_observed_volume_change_fraction": float(
                fmean(
                    row.observed_volume_change_fraction
                    for row in group
                )
            ),
        }

    return result


def _write_csv(path: Path, rows: list[Stage9ValidationRow]) -> None:
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


def validate_stage9_model(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    data_audit_root: Path,
    stage8_selection_root: Path,
    stage9_selection_root: Path,
    stage9_validation_plan_root: Path,
    cache_root: Path,
    output_dir: Path,
    workers: int = 1,
    allow_dirty: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Stage9ValidationArtifact:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Stage 9 validation destination exists: {destination}"
        )
    if workers < 1:
        raise ValueError("workers must be at least 1")

    repository = read_repository_state(repo_root.resolve())
    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Stage 9 reserve validation requires a clean Git tree"
        )

    audit = load_sealed_stage8_data_audit(data_audit_root)
    selected_stage8 = load_selected_stage8_model(
        stage8_selection_root
    )
    selected_stage9 = load_selected_stage9_model(
        stage9_selection_root
    )
    plan = load_stage9_validation_plan(
        stage9_validation_plan_root
    )

    audit_sha = sha256_file(
        data_audit_root.resolve() / "stage8_data_audit.json"
    )
    stage8_selection_sha = sha256_file(
        stage8_selection_root.resolve() / "stage8_model_selection.json"
    )
    stage9_selection_sha = sha256_file(
        stage9_selection_root.resolve() / "stage9_delayed_selection.json"
    )
    stage8_protocol_sha = sha256_file(stage8_protocol_path.resolve())
    experiment_sha = sha256_file(experiment_config_path.resolve())

    if selected_stage8.stage8_data_audit_sha256 != audit_sha:
        raise ValueError("Stage 8 selection does not match data audit")
    if selected_stage9.stage8_data_audit_sha256 != audit_sha:
        raise ValueError("Stage 9 selection does not match data audit")
    if (
        selected_stage9.stage8_model_selection_sha256
        != stage8_selection_sha
    ):
        raise ValueError("Stage 9 selection does not match Stage 8 selection")
    if selected_stage9.stage8_protocol_sha256 != stage8_protocol_sha:
        raise ValueError("Stage 9 selection does not match Stage 8 protocol")
    if selected_stage9.experiment_config_sha256 != experiment_sha:
        raise ValueError("Stage 9 selection does not match experiment config")
    if plan.stage8_data_audit_sha256 != audit_sha:
        raise ValueError("Stage 9 validation plan does not match audit")
    if plan.stage9_selection_sha256 != stage9_selection_sha:
        raise ValueError("Stage 9 validation plan does not match selection")
    if not set(plan.patient_ids).issubset(
        selected_stage9.reserve_patient_ids
    ):
        raise ValueError(
            "Stage 9 validation plan contains a non-reserve patient"
        )
    if set(plan.patient_ids) & set(
        selected_stage9.untouched_holdout_patient_ids
    ):
        raise ValueError(
            "Stage 9 validation plan intersects untouched holdout"
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
        patient_ids=plan.patient_ids,
        require_spatial_rtdose=(
            selected_stage8.candidate.use_spatial_rtdose
        ),
    )
    if issues:
        preview = "\n".join(
            f"  patient {item.patient_id}: {item.input_name} -> "
            f"{item.expected_path}"
            for item in issues[:40]
        )
        raise FileNotFoundError(
            "Stage 9 reserve validation preflight failed before t2 "
            "loading:\n" + preview
        )

    observation = _observation_parameters(stage8_protocol_path)
    calibration_config = _calibration_config(
        stage8_protocol_path=stage8_protocol_path,
        experiment_config_path=experiment_config_path,
    )
    treatment = CFBTreatmentMetadata(metadata_root)
    radiobiology = RadiobiologyParameters(
        alpha_per_gy=(
            selected_stage8.candidate.effective_alpha_per_gy
        ),
        alpha_beta_ratio_gy=(
            selected_stage8.candidate.alpha_beta_ratio_gy
        ),
    )
    delayed = DelayedResponseParameters(
        damage_transfer_fraction=(
            selected_stage9.candidate.damage_transfer_fraction
        ),
        damage_half_life_days=(
            selected_stage9.candidate.damage_half_life_days
        ),
        damaged_visibility=(
            selected_stage9.candidate.damaged_visibility
        ),
    )

    if progress is not None:
        progress(
            f"[stage9-validation] preflight passed: "
            f"{len(plan.patient_ids)} sealed reserve patients"
        )

    rows: list[Stage9ValidationRow] = []

    for index, patient_id in enumerate(plan.patient_ids, start=1):
        started = time.perf_counter()
        if progress is not None:
            progress(
                f"[stage9-validation] patient {patient_id} "
                f"({index}/{len(plan.patient_ids)}): "
                "loading t0/t1 only"
            )

        inputs = prepare_stage8_forecast_inputs(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=experiment.evaluation.target_spacing,
            treatment=treatment,
            observation_parameters=observation,
            load_spatial_rtdose=(
                selected_stage8.candidate.use_spatial_rtdose
            ),
            require_spatial_rtdose=(
                selected_stage8.candidate.use_spatial_rtdose
            ),
        )
        rt = build_stage8_radiotherapy_events(
            inputs.schedule,
            radiobiology,
            proliferation_survival=(
                selected_stage8.candidate.proliferation_survival
            ),
            cumulative_rtdose=(
                inputs.cumulative_rtdose
                if selected_stage8.candidate.use_spatial_rtdose
                else None
            ),
        )

        def calibration_progress(message: str) -> None:
            if progress is not None:
                progress(
                    f"[stage9-validation]   patient={patient_id}: "
                    f"{message}"
                )

        calibration = calibrate_stage8_interval(
            initial_state=inputs.initial_state,
            observed_mask=inputs.observed.gtv.data > 0.5,
            domain_mask=inputs.domain_mask,
            spacing=inputs.start.spacing,
            duration_days=(
                inputs.observed.days_from_baseline
                - inputs.start.days_from_baseline
            ),
            start_time_day=inputs.start.days_from_baseline,
            fraction_events=_events_for_interval(
                rt.events,
                start_day=inputs.start.days_from_baseline,
                end_day=inputs.observed.days_from_baseline,
            ),
            config=calibration_config,
            cache_dir=(
                cache_root.resolve()
                / f"patient-{patient_id}"
                / selected_stage8.candidate.candidate_id
            ),
            workers=workers,
            progress=calibration_progress,
        )

        if progress is not None:
            progress(
                f"[stage9-validation] patient {patient_id}: "
                "D/rho frozen; revealing t2"
            )

        target = prepare_stage8_evaluation_target(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=experiment.evaluation.target_spacing,
            reference=inputs.observed,
        )
        forecast = simulate_stage9_forecast(
            inputs=inputs,
            target_day=target.target.days_from_baseline,
            growth=ReactionDiffusionParameters(
                diffusion=calibration.best.diffusion,
                proliferation=calibration.best.proliferation,
            ),
            radiobiology=radiobiology,
            proliferation_survival=(
                selected_stage8.candidate.proliferation_survival
            ),
            delayed=delayed,
            dt_days=experiment.evaluation.dt,
            observation_parameters=observation,
        )

        observed_t2 = np.asarray(
            target.target.gtv.data > 0.5,
            dtype=bool,
        )
        persistence = np.asarray(
            inputs.observed.gtv.data > 0.5,
            dtype=bool,
        )
        predicted = forecast.prediction_mask

        twin_dice = dice_score(predicted, observed_t2)
        persistence_dice = dice_score(persistence, observed_t2)
        t1_volume = _mask_volume_cm3(
            persistence,
            spacing=target.target.spacing,
        )
        t2_volume = _mask_volume_cm3(
            observed_t2,
            spacing=target.target.spacing,
        )
        predicted_volume = _mask_volume_cm3(
            predicted,
            spacing=target.target.spacing,
        )
        volume_change = (
            0.0
            if t1_volume <= 0.0
            else (t2_volume - t1_volume) / t1_volume
        )

        rows.append(
            Stage9ValidationRow(
                patient_id=patient_id,
                diffusion=calibration.best.diffusion,
                proliferation=calibration.best.proliferation,
                calibration_dice=calibration.best.dice,
                calibration_loss=calibration.best.loss,
                calibration_identifiable=(
                    calibration.diagnostics.identifiable
                ),
                twin_dice=twin_dice,
                persistence_dice=persistence_dice,
                delta_vs_persistence=twin_dice - persistence_dice,
                twin_relative_volume_error=relative_volume_error(
                    predicted,
                    observed_t2,
                ),
                persistence_relative_volume_error=(
                    relative_volume_error(
                        persistence,
                        observed_t2,
                    )
                ),
                twin_hd95_mm=hausdorff95_mm(
                    predicted,
                    observed_t2,
                    spacing=target.target.spacing,
                ),
                persistence_hd95_mm=hausdorff95_mm(
                    persistence,
                    observed_t2,
                    spacing=target.target.spacing,
                ),
                twin_centroid_distance_mm=centroid_distance_mm(
                    predicted,
                    observed_t2,
                    spacing=target.target.spacing,
                ),
                persistence_centroid_distance_mm=centroid_distance_mm(
                    persistence,
                    observed_t2,
                    spacing=target.target.spacing,
                ),
                t1_day=inputs.observed.days_from_baseline,
                t2_day=target.target.days_from_baseline,
                forecast_horizon_days=(
                    target.target.days_from_baseline
                    - inputs.observed.days_from_baseline
                ),
                days_last_rt_to_t1=(
                    inputs.observed.days_from_baseline
                    - max(inputs.schedule.fraction_days)
                ),
                observed_t1_volume_cm3=t1_volume,
                observed_t2_volume_cm3=t2_volume,
                predicted_t2_volume_cm3=predicted_volume,
                observed_volume_change_fraction=volume_change,
            )
        )

        if progress is not None:
            progress(
                f"[stage9-validation] patient {patient_id} done in "
                f"{time.perf_counter() - started:.1f}s; "
                f"Dice={twin_dice:.4f}; "
                f"persistence={persistence_dice:.4f}; "
                f"delta={twin_dice - persistence_dice:+.4f}"
            )

    deltas = [row.delta_vs_persistence for row in rows]
    twin_dice_values = [row.twin_dice for row in rows]
    persistence_dice_values = [
        row.persistence_dice
        for row in rows
    ]

    payload: dict[str, object] = {
        "schema_version": STAGE9_VALIDATION_SCHEMA_VERSION,
        "kind": "stage9_reserve_internal_validation",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "stage8_model_selection_sha256": stage8_selection_sha,
            "stage9_selection_sha256": stage9_selection_sha,
            "stage9_validation_plan_sha256": sha256_file(
                stage9_validation_plan_root.resolve()
                / "stage9_validation_plan.json"
            ),
            "stage8_protocol_sha256": stage8_protocol_sha,
            "experiment_config_sha256": experiment_sha,
        },
        "selected_stage8_candidate": {
            "candidate_id": selected_stage8.candidate.candidate_id,
            "effective_alpha_per_gy": (
                selected_stage8.candidate.effective_alpha_per_gy
            ),
            "alpha_beta_ratio_gy": (
                selected_stage8.candidate.alpha_beta_ratio_gy
            ),
            "proliferation_survival": (
                selected_stage8.candidate.proliferation_survival
            ),
            "use_spatial_rtdose": (
                selected_stage8.candidate.use_spatial_rtdose
            ),
        },
        "selected_stage9_candidate": asdict(
            selected_stage9.candidate
        ),
        "leakage_control": {
            "global_model_selection_changed": False,
            "patient_specific_d_rho_uses_t2": False,
            "reserve_t2_loaded_only_after_d_rho_freeze": True,
            "reserve_validation_patient_ids": list(plan.patient_ids),
            "untouched_holdout_t2_loaded": False,
        },
        "summary": {
            "patient_count": len(rows),
            "mean_twin_dice": float(fmean(twin_dice_values)),
            "median_twin_dice": float(median(twin_dice_values)),
            "mean_persistence_dice": float(
                fmean(persistence_dice_values)
            ),
            "mean_delta_vs_persistence": float(fmean(deltas)),
            "median_delta_vs_persistence": float(median(deltas)),
            "better_count": sum(value > 1e-6 for value in deltas),
            "equal_count": sum(abs(value) <= 1e-6 for value in deltas),
            "worse_count": sum(value < -1e-6 for value in deltas),
            "catastrophic_failure_count": sum(
                value < -0.10
                for value in deltas
            ),
            "mean_twin_hd95_mm": _optional_mean(
                [row.twin_hd95_mm for row in rows]
            ),
            "mean_persistence_hd95_mm": _optional_mean(
                [row.persistence_hd95_mm for row in rows]
            ),
        },
        "trajectory_analysis": _trajectory_summary(rows),
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
        manifest_path = temporary / "stage9_internal_validation.json"
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
        (temporary / "stage9_internal_validation.sha256").write_text(
            sha256_file(manifest_path)
            + "  stage9_internal_validation.json\n",
            encoding="ascii",
        )
        _write_csv(
            temporary / "stage9_internal_validation.csv",
            rows,
        )
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return Stage9ValidationArtifact(
        directory=destination,
        manifest=payload,
    )
