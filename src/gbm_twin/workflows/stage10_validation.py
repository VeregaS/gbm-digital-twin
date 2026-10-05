from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path
from statistics import (
    fmean,
    median,
)

import numpy as np

from gbm_twin.calibration.stage8 import (
    calibrate_stage8_interval,
)
from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)
from gbm_twin.workflows.repository import (
    read_repository_state,
)
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_patient import (
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage8_treatment import (
    build_stage8_radiotherapy_events,
)
from gbm_twin.workflows.stage8_validation import (
    preflight_stage8_validation_inputs,
)
from gbm_twin.workflows.stage9_validation import (
    _calibration_config,
    _events_for_interval,
    _mask_volume_cm3,
    _observation_parameters,
    _optional_mean,
    _trajectory_group,
)
from gbm_twin.workflows.stage10_forecast import (
    simulate_stage10_forecast,
)
from gbm_twin.workflows.stage10_selection_artifact import (
    load_selected_stage10_model,
)
from gbm_twin.workflows.stage10_validation_plan import (
    load_stage10_validation_plan,
    verify_stage10_validation_cohort,
)
from gbm_twin.workflows.stage10_validation_protocol import (
    Stage10ValidationConfig,
    load_stage10_validation_config,
    verify_frozen_stage10_model,
)

STAGE10_VALIDATION_SCHEMA_VERSION = 1
STAGE10_VALIDATION_KIND = (
    "stage10_reserve_internal_validation"
)


@dataclass(frozen=True)
class Stage10ValidationRow:
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
    trajectory_group: str


@dataclass(frozen=True)
class Stage10ValidationArtifact:
    directory: Path
    manifest: dict[str, object]


def _trajectory_summary(
    rows: list[
        Stage10ValidationRow
    ],
) -> dict[str, object]:
    result: dict[
        str,
        object,
    ] = {}

    for name in (
        "growth",
        "stable",
        "regression",
    ):
        group = [
            row
            for row in rows
            if row.trajectory_group
            == name
        ]

        if not group:
            result[
                name
            ] = {
                "patient_count": 0,
            }

            continue

        result[
            name
        ] = {
            "patient_count": len(
                group
            ),
            "patient_ids": sorted(
                row.patient_id
                for row in group
            ),
            "mean_dice": float(
                fmean(
                    row.twin_dice
                    for row in group
                )
            ),
            "mean_delta_vs_persistence": (
                float(
                    fmean(
                        row
                        .delta_vs_persistence
                        for row in group
                    )
                )
            ),
            "mean_hd95_mm": (
                _optional_mean(
                    [
                        row.twin_hd95_mm
                        for row in group
                    ]
                )
            ),
            "mean_observed_volume_change_fraction": (
                float(
                    fmean(
                        row
                        .observed_volume_change_fraction
                        for row in group
                    )
                )
            ),
        }

    return result


def _bootstrap_mean_delta_ci(
    deltas: list[float],
    *,
    samples: int,
    seed: int,
) -> tuple[
    float,
    float,
]:
    values = np.asarray(
        deltas,
        dtype=np.float64,
    )

    if values.size == 0:
        raise ValueError(
            "Cannot bootstrap an empty validation cohort"
        )

    rng = np.random.default_rng(
        seed
    )

    indices = rng.integers(
        0,
        values.size,
        size=(
            samples,
            values.size,
        ),
    )

    means = values[
        indices
    ].mean(
        axis=1
    )

    low, high = np.quantile(
        means,
        [
            0.025,
            0.975,
        ],
    )

    return (
        float(
            low
        ),
        float(
            high
        ),
    )


def evaluate_stage10_validation_summary(
    summary: dict[str, object],
    config: Stage10ValidationConfig,
) -> tuple[
    str,
    tuple[str, ...],
]:
    numeric_keys = (
        "mean_delta_vs_persistence",
        "median_delta_vs_persistence",
        "mean_twin_relative_volume_error",
        "mean_persistence_relative_volume_error",
    )
    for key in numeric_keys:
        value = summary[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not np.isfinite(value)
        ):
            raise ValueError(f"{key} must be a finite number")
    for key in ("mean_twin_hd95_mm", "mean_persistence_hd95_mm"):
        value = summary.get(key)
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not np.isfinite(value)
            or value < 0.0
        ):
            raise ValueError(f"{key} must be finite and non-negative or None")
    count = summary["catastrophic_failure_count"]
    if type(count) is not int or count < 0:
        raise ValueError("catastrophic_failure_count must be a non-negative integer")

    reasons: list[str] = []

    mean_delta = float(
        summary[
            "mean_delta_vs_persistence"
        ]
    )

    median_delta = float(
        summary[
            "median_delta_vs_persistence"
        ]
    )

    catastrophic = int(
        summary[
            "catastrophic_failure_count"
        ]
    )

    if (
        mean_delta
        <= config
        .min_mean_delta_vs_persistence
    ):
        reasons.append(
            "mean_delta_vs_persistence"
        )

    if (
        median_delta
        < config
        .min_median_delta_vs_persistence
    ):
        reasons.append(
            "median_delta_vs_persistence"
        )

    if (
        catastrophic
        > config
        .max_catastrophic_failure_count
    ):
        reasons.append(
            "catastrophic_failure_count"
        )

    if (
        config
        .require_mean_rve_not_worse_than_persistence
        and float(
            summary[
                "mean_twin_relative_volume_error"
            ]
        )
        > float(
            summary[
                "mean_persistence_relative_volume_error"
            ]
        )
    ):
        reasons.append(
            "mean_relative_volume_error"
        )

    twin_hd95 = summary.get(
        "mean_twin_hd95_mm"
    )

    persistence_hd95 = (
        summary.get(
            "mean_persistence_hd95_mm"
        )
    )

    if (
        config
        .require_mean_hd95_not_worse_than_persistence
    ):
        if (
            twin_hd95 is None
            or persistence_hd95
            is None
            or float(
                twin_hd95
            )
            > float(
                persistence_hd95
            )
        ):
            reasons.append(
                "mean_hd95_mm"
            )

    return (
        (
            "validation_passed"
            if not reasons
            else "validation_failed"
        ),
        tuple(
            reasons
        ),
    )


def _write_csv(
    path: Path,
    rows: list[
        Stage10ValidationRow
    ],
) -> None:
    if not rows:
        return

    fieldnames = list(
        asdict(
            rows[
                0
            ]
        ).keys()
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                asdict(
                    row
                )
            )


def _patient_progress_callback(
    progress: Callable[
        [str],
        None,
    ]
    | None,
    *,
    patient_id: int,
) -> Callable[
    [str],
    None,
]:
    def emit(
        message: str,
    ) -> None:
        if progress is not None:
            progress(
                "[stage10-validation]   "
                f"patient={patient_id}: "
                f"{message}"
            )

    return emit


def validate_stage10_model(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    data_audit_root: Path,
    stage8_selection_root: Path,
    stage10_selection_root: Path,
    frozen_model_config_path: Path,
    validation_config_path: Path,
    validation_plan_root: Path,
    cache_root: Path,
    output_dir: Path,
    workers: int = 1,
    allow_dirty: bool = False,
    progress: Callable[
        [str],
        None,
    ]
    | None = None,
) -> Stage10ValidationArtifact:
    destination = (
        output_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            "Stage 10 validation destination exists: "
            f"{destination}"
        )

    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    repository = (
        read_repository_state(
            repo_root.resolve()
        )
    )

    if (
        repository.dirty
        and not allow_dirty
    ):
        raise ValueError(
            "Stage 10 reserve validation requires a clean Git tree"
        )

    audit = load_sealed_stage8_data_audit(
        data_audit_root
    )

    selected_stage8 = (
        load_selected_stage8_model(
            stage8_selection_root
        )
    )

    selected_stage10 = (
        load_selected_stage10_model(
            stage10_selection_root
        )
    )

    frozen = (
        verify_frozen_stage10_model(
            selected=(
                selected_stage10
            ),
            config_path=(
                frozen_model_config_path
            ),
        )
    )

    validation = (
        load_stage10_validation_config(
            validation_config_path
        )
    )

    plan = (
        load_stage10_validation_plan(
            validation_plan_root
        )
    )

    audit_sha = (
        sha256_file(
            data_audit_root.resolve()
            / "stage8_data_audit.json"
        )
    )

    stage8_selection_sha = (
        sha256_file(
            stage8_selection_root.resolve()
            / "stage8_model_selection.json"
        )
    )

    stage10_selection_sha = (
        sha256_file(
            stage10_selection_root.resolve()
            / "stage10_decoupled_selection.json"
        )
    )

    stage8_protocol_sha = (
        sha256_file(
            stage8_protocol_path.resolve()
        )
    )

    experiment_sha = (
        sha256_file(
            experiment_config_path.resolve()
        )
    )

    frozen_config_sha = (
        sha256_file(
            frozen_model_config_path.resolve()
        )
    )

    validation_config_sha = (
        sha256_file(
            validation_config_path.resolve()
        )
    )

    plan_sha = (
        sha256_file(
            validation_plan_root.resolve()
            / "stage10_validation_plan.json"
        )
    )

    if (
        selected_stage8
        .stage8_data_audit_sha256
        != audit_sha
    ):
        raise ValueError(
            "Stage 8 selection does not match data audit"
        )

    if (
        selected_stage10
        .stage8_data_audit_sha256
        != audit_sha
    ):
        raise ValueError(
            "Stage 10 selection does not match data audit"
        )

    if (
        selected_stage10
        .stage8_model_selection_sha256
        != stage8_selection_sha
    ):
        raise ValueError(
            "Stage 10 selection does not match Stage 8 selection"
        )

    if (
        selected_stage10
        .stage8_protocol_sha256
        != stage8_protocol_sha
    ):
        raise ValueError(
            "Stage 10 selection does not match Stage 8 protocol"
        )

    if (
        selected_stage10
        .experiment_config_sha256
        != experiment_sha
    ):
        raise ValueError(
            "Stage 10 selection does not match experiment config"
        )

    if (
        plan
        .stage8_data_audit_sha256
        != audit_sha
    ):
        raise ValueError(
            "Stage 10 validation plan does not match data audit"
        )

    if (
        plan
        .stage10_selection_sha256
        != stage10_selection_sha
    ):
        raise ValueError(
            "Stage 10 validation plan does not match selection"
        )

    if (
        plan
        .frozen_model_config_sha256
        != frozen_config_sha
    ):
        raise ValueError(
            "Stage 10 validation plan does not match frozen model config"
        )

    if (
        plan
        .validation_config_sha256
        != validation_config_sha
    ):
        raise ValueError(
            "Stage 10 validation plan does not match validation config"
        )

    verify_stage10_validation_cohort(
        plan,
        audit_manifest=audit.manifest,
        reserve_patient_ids=selected_stage10.reserve_patient_ids,
        untouched_holdout_patient_ids=selected_stage10.untouched_holdout_patient_ids,
        count=validation.patient_count,
        seed=validation.seed,
    )

    experiment = (
        load_cohort_experiment_config(
            experiment_config_path
        )
    )

    metadata_root = (
        experiment.metadata_root
        if experiment
        .metadata_root
        .is_absolute()
        else (
            repo_root.resolve()
            / experiment.metadata_root
        )
    )

    patients_root = (
        experiment.patients_root
        if experiment
        .patients_root
        .is_absolute()
        else (
            repo_root.resolve()
            / experiment.patients_root
        )
    )

    issues = (
        preflight_stage8_validation_inputs(
            patients_root=(
                patients_root
            ),
            patient_ids=(
                plan.patient_ids
            ),
            require_spatial_rtdose=(
                selected_stage8
                .candidate
                .use_spatial_rtdose
            ),
        )
    )

    if issues:
        preview = "\n".join(
            (
                f"  patient {item.patient_id}: "
                f"{item.input_name} -> "
                f"{item.expected_path}"
            )
            for item in (
                issues[
                    :40
                ]
            )
        )

        raise FileNotFoundError(
            "Stage 10 reserve validation preflight failed before t2 "
            "loading:\n"
            + preview
        )

    observation = (
        _observation_parameters(
            stage8_protocol_path
        )
    )

    calibration_config = (
        _calibration_config(
            stage8_protocol_path=(
                stage8_protocol_path
            ),
            experiment_config_path=(
                experiment_config_path
            ),
        )
    )

    treatment = (
        CFBTreatmentMetadata(
            metadata_root
        )
    )

    radiobiology = (
        RadiobiologyParameters(
            alpha_per_gy=(
                selected_stage8
                .candidate
                .effective_alpha_per_gy
            ),
            alpha_beta_ratio_gy=(
                selected_stage8
                .candidate
                .alpha_beta_ratio_gy
            ),
        )
    )

    if progress is not None:
        progress(
            "[stage10-validation] preflight passed: "
            f"{len(plan.patient_ids)} sealed reserve patients"
        )

    rows: list[
        Stage10ValidationRow
    ] = []

    for (
        index,
        patient_id,
    ) in enumerate(
        plan.patient_ids,
        start=1,
    ):
        started = (
            time.perf_counter()
        )

        if progress is not None:
            progress(
                "[stage10-validation] "
                f"patient {patient_id} "
                f"({index}/{len(plan.patient_ids)}): "
                "loading t0/t1 only"
            )

        inputs = (
            prepare_stage8_forecast_inputs(
                metadata_root=(
                    metadata_root
                ),
                patients_root=(
                    patients_root
                ),
                patient_id=patient_id,
                target_spacing=(
                    experiment
                    .evaluation
                    .target_spacing
                ),
                treatment=treatment,
                observation_parameters=(
                    observation
                ),
                load_spatial_rtdose=(
                    selected_stage8
                    .candidate
                    .use_spatial_rtdose
                ),
                require_spatial_rtdose=(
                    selected_stage8
                    .candidate
                    .use_spatial_rtdose
                ),
            )
        )

        rt = (
            build_stage8_radiotherapy_events(
                inputs.schedule,
                radiobiology,
                proliferation_survival=(
                    selected_stage8
                    .candidate
                    .proliferation_survival
                ),
                cumulative_rtdose=(
                    inputs.cumulative_rtdose
                    if selected_stage8
                    .candidate
                    .use_spatial_rtdose
                    else None
                ),
            )
        )

        calibration = (
            calibrate_stage8_interval(
                initial_state=(
                    inputs
                    .initial_state
                ),
                observed_mask=(
                    inputs
                    .observed
                    .gtv
                    .data
                    > 0.5
                ),
                domain_mask=(
                    inputs
                    .domain_mask
                ),
                spacing=(
                    inputs
                    .start
                    .spacing
                ),
                duration_days=(
                    inputs
                    .observed
                    .days_from_baseline
                    - inputs
                    .start
                    .days_from_baseline
                ),
                start_time_day=(
                    inputs
                    .start
                    .days_from_baseline
                ),
                fraction_events=(
                    _events_for_interval(
                        rt.events,
                        start_day=(
                            inputs
                            .start
                            .days_from_baseline
                        ),
                        end_day=(
                            inputs
                            .observed
                            .days_from_baseline
                        ),
                    )
                ),
                config=(
                    calibration_config
                ),
                cache_dir=(
                    cache_root.resolve()
                    / f"patient-{patient_id}"
                    / selected_stage8
                    .candidate
                    .candidate_id
                ),
                workers=workers,
                progress=(
                    _patient_progress_callback(
                        progress,
                        patient_id=(
                            patient_id
                        ),
                    )
                ),
            )
        )

        if progress is not None:
            progress(
                "[stage10-validation] "
                f"patient {patient_id}: "
                "D/rho frozen; revealing t2"
            )

        target = (
            prepare_stage8_evaluation_target(
                metadata_root=(
                    metadata_root
                ),
                patients_root=(
                    patients_root
                ),
                patient_id=patient_id,
                target_spacing=(
                    experiment
                    .evaluation
                    .target_spacing
                ),
                reference=(
                    inputs
                    .observed
                ),
            )
        )

        forecast = (
            simulate_stage10_forecast(
                inputs=inputs,
                target_day=(
                    target
                    .target
                    .days_from_baseline
                ),
                growth=(
                    ReactionDiffusionParameters(
                        diffusion=(
                            calibration
                            .best
                            .diffusion
                        ),
                        proliferation=(
                            calibration
                            .best
                            .proliferation
                        ),
                    )
                ),
                radiobiology=(
                    radiobiology
                ),
                proliferation_survival=(
                    selected_stage8
                    .candidate
                    .proliferation_survival
                ),
                damage_half_life_days=(
                    frozen
                    .visible_damage_half_life_days
                ),
                dt_days=(
                    experiment
                    .evaluation
                    .dt
                ),
                observation_parameters=(
                    observation
                ),
            )
        )

        observed_t2 = np.asarray(
            target
            .target
            .gtv
            .data
            > 0.5,
            dtype=bool,
        )

        persistence = np.asarray(
            inputs
            .observed
            .gtv
            .data
            > 0.5,
            dtype=bool,
        )

        predicted = (
            forecast
            .prediction_mask
        )

        twin_dice = (
            dice_score(
                predicted,
                observed_t2,
            )
        )

        persistence_dice = (
            dice_score(
                persistence,
                observed_t2,
            )
        )

        t1_volume = (
            _mask_volume_cm3(
                persistence,
                spacing=(
                    target
                    .target
                    .spacing
                ),
            )
        )

        t2_volume = (
            _mask_volume_cm3(
                observed_t2,
                spacing=(
                    target
                    .target
                    .spacing
                ),
            )
        )

        predicted_volume = (
            _mask_volume_cm3(
                predicted,
                spacing=(
                    target
                    .target
                    .spacing
                ),
            )
        )

        volume_change = (
            0.0
            if t1_volume
            <= 0.0
            else (
                t2_volume
                - t1_volume
            )
            / t1_volume
        )

        rows.append(
            Stage10ValidationRow(
                patient_id=(
                    patient_id
                ),
                diffusion=(
                    calibration
                    .best
                    .diffusion
                ),
                proliferation=(
                    calibration
                    .best
                    .proliferation
                ),
                calibration_dice=(
                    calibration
                    .best
                    .dice
                ),
                calibration_loss=(
                    calibration
                    .best
                    .loss
                ),
                calibration_identifiable=(
                    calibration
                    .diagnostics
                    .identifiable
                ),
                twin_dice=(
                    twin_dice
                ),
                persistence_dice=(
                    persistence_dice
                ),
                delta_vs_persistence=(
                    twin_dice
                    - persistence_dice
                ),
                twin_relative_volume_error=(
                    relative_volume_error(
                        predicted,
                        observed_t2,
                    )
                ),
                persistence_relative_volume_error=(
                    relative_volume_error(
                        persistence,
                        observed_t2,
                    )
                ),
                twin_hd95_mm=(
                    hausdorff95_mm(
                        predicted,
                        observed_t2,
                        spacing=(
                            target
                            .target
                            .spacing
                        ),
                    )
                ),
                persistence_hd95_mm=(
                    hausdorff95_mm(
                        persistence,
                        observed_t2,
                        spacing=(
                            target
                            .target
                            .spacing
                        ),
                    )
                ),
                twin_centroid_distance_mm=(
                    centroid_distance_mm(
                        predicted,
                        observed_t2,
                        spacing=(
                            target
                            .target
                            .spacing
                        ),
                    )
                ),
                persistence_centroid_distance_mm=(
                    centroid_distance_mm(
                        persistence,
                        observed_t2,
                        spacing=(
                            target
                            .target
                            .spacing
                        ),
                    )
                ),
                t1_day=(
                    inputs
                    .observed
                    .days_from_baseline
                ),
                t2_day=(
                    target
                    .target
                    .days_from_baseline
                ),
                forecast_horizon_days=(
                    target
                    .target
                    .days_from_baseline
                    - inputs
                    .observed
                    .days_from_baseline
                ),
                days_last_rt_to_t1=(
                    inputs
                    .observed
                    .days_from_baseline
                    - max(
                        inputs
                        .schedule
                        .fraction_days
                    )
                ),
                observed_t1_volume_cm3=(
                    t1_volume
                ),
                observed_t2_volume_cm3=(
                    t2_volume
                ),
                predicted_t2_volume_cm3=(
                    predicted_volume
                ),
                observed_volume_change_fraction=(
                    volume_change
                ),
                trajectory_group=(
                    _trajectory_group(
                        volume_change
                    )
                ),
            )
        )

        if progress is not None:
            progress(
                "[stage10-validation] "
                f"patient {patient_id} done in "
                f"{time.perf_counter() - started:.1f}s; "
                f"Dice={twin_dice:.4f}; "
                f"persistence={persistence_dice:.4f}; "
                "delta="
                f"{twin_dice - persistence_dice:+.4f}"
            )

    deltas = [
        row.delta_vs_persistence
        for row in rows
    ]

    twin_dice_values = [
        row.twin_dice
        for row in rows
    ]

    persistence_dice_values = [
        row.persistence_dice
        for row in rows
    ]

    twin_rve = [
        row.twin_relative_volume_error
        for row in rows
    ]

    persistence_rve = [
        row.persistence_relative_volume_error
        for row in rows
    ]

    bootstrap_low, bootstrap_high = (
        _bootstrap_mean_delta_ci(
            deltas,
            samples=(
                validation
                .bootstrap_samples
            ),
            seed=(
                validation
                .bootstrap_seed
            ),
        )
    )

    summary: dict[
        str,
        object,
    ] = {
        "patient_count": len(
            rows
        ),
        "mean_twin_dice": float(
            fmean(
                twin_dice_values
            )
        ),
        "median_twin_dice": float(
            median(
                twin_dice_values
            )
        ),
        "mean_persistence_dice": float(
            fmean(
                persistence_dice_values
            )
        ),
        "median_persistence_dice": float(
            median(
                persistence_dice_values
            )
        ),
        "mean_delta_vs_persistence": float(
            fmean(
                deltas
            )
        ),
        "median_delta_vs_persistence": float(
            median(
                deltas
            )
        ),
        "bootstrap_mean_delta_ci95": [
            bootstrap_low,
            bootstrap_high,
        ],
        "better_count": sum(
            value > 1e-6
            for value in deltas
        ),
        "equal_count": sum(
            abs(
                value
            )
            <= 1e-6
            for value in deltas
        ),
        "worse_count": sum(
            value < -1e-6
            for value in deltas
        ),
        "catastrophic_failure_count": sum(
            value
            < validation
            .catastrophic_delta_vs_persistence
            for value in deltas
        ),
        "mean_twin_relative_volume_error": (
            float(
                fmean(
                    twin_rve
                )
            )
        ),
        "mean_persistence_relative_volume_error": (
            float(
                fmean(
                    persistence_rve
                )
            )
        ),
        "mean_twin_hd95_mm": (
            _optional_mean(
                [
                    row.twin_hd95_mm
                    for row in rows
                ]
            )
        ),
        "mean_persistence_hd95_mm": (
            _optional_mean(
                [
                    row.persistence_hd95_mm
                    for row in rows
                ]
            )
        ),
        "mean_twin_centroid_distance_mm": (
            _optional_mean(
                [
                    row
                    .twin_centroid_distance_mm
                    for row in rows
                ]
            )
        ),
        "mean_persistence_centroid_distance_mm": (
            _optional_mean(
                [
                    row
                    .persistence_centroid_distance_mm
                    for row in rows
                ]
            )
        ),
    }

    decision, failed_guardrails = (
        evaluate_stage10_validation_summary(
            summary,
            validation,
        )
    )

    payload: dict[
        str,
        object,
    ] = {
        "schema_version": (
            STAGE10_VALIDATION_SCHEMA_VERSION
        ),
        "kind": (
            STAGE10_VALIDATION_KIND
        ),
        "sealed": True,
        "repository": {
            "commit_sha": (
                repository
                .commit_sha
            ),
            "dirty": (
                repository
                .dirty
            ),
        },
        "source": {
            "stage8_data_audit_sha256": (
                audit_sha
            ),
            "stage8_model_selection_sha256": (
                stage8_selection_sha
            ),
            "stage10_selection_sha256": (
                stage10_selection_sha
            ),
            "stage10_validation_plan_sha256": (
                plan_sha
            ),
            "frozen_model_config_sha256": (
                frozen_config_sha
            ),
            "validation_config_sha256": (
                validation_config_sha
            ),
            "stage8_protocol_sha256": (
                stage8_protocol_sha
            ),
            "experiment_config_sha256": (
                experiment_sha
            ),
        },
        "frozen_model": {
            "model_id": (
                frozen.model_id
            ),
            "kind": (
                frozen
                .candidate_kind
            ),
            "visible_damage_half_life_days": (
                frozen
                .visible_damage_half_life_days
            ),
        },
        "leakage_control": {
            "global_model_selection_changed": False,
            "patient_specific_d_rho_uses_t2": False,
            "reserve_t2_loaded_only_after_d_rho_freeze": True,
            "reserve_validation_patient_ids": (
                list(
                    plan
                    .patient_ids
                )
            ),
            "remaining_reserve_patient_ids": (
                list(
                    plan
                    .remaining_reserve_patient_ids
                )
            ),
            "untouched_holdout_t2_loaded": False,
        },
        "advancement_guardrails": {
            "min_mean_delta_vs_persistence": (
                validation
                .min_mean_delta_vs_persistence
            ),
            "min_median_delta_vs_persistence": (
                validation
                .min_median_delta_vs_persistence
            ),
            "max_catastrophic_failure_count": (
                validation
                .max_catastrophic_failure_count
            ),
            "require_mean_rve_not_worse_than_persistence": (
                validation
                .require_mean_rve_not_worse_than_persistence
            ),
            "require_mean_hd95_not_worse_than_persistence": (
                validation
                .require_mean_hd95_not_worse_than_persistence
            ),
        },
        "summary": (
            summary
        ),
        "trajectory_analysis": (
            _trajectory_summary(
                rows
            )
        ),
        "decision": (
            decision
        ),
        "failed_guardrails": (
            list(
                failed_guardrails
            )
        ),
        "next_step": (
            validation
            .next_step_if_passed
            if decision
            == "validation_passed"
            else (
                validation
                .next_step_if_failed
            )
        ),
        "patients": [
            asdict(
                row
            )
            for row in rows
        ],
    }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=(
                destination.parent
            ),
            prefix=(
                f".{destination.name}-"
            ),
        )
    )

    try:
        manifest_path = (
            temporary
            / "stage10_internal_validation.json"
        )

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

        (
            temporary
            / "stage10_internal_validation.sha256"
        ).write_text(
            (
                sha256_file(
                    manifest_path
                )
                + "  stage10_internal_validation.json\n"
            ),
            encoding="ascii",
        )

        _write_csv(
            (
                temporary
                / "stage10_internal_validation.csv"
            ),
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

    return Stage10ValidationArtifact(
        directory=(
            destination
        ),
        manifest=(
            payload
        ),
    )
