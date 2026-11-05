from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean, median
from typing import Literal

Trajectory = Literal[
    "growth",
    "stable",
    "regression",
    "unknown",
]


@dataclass(frozen=True)
class CohortPatientErrorRecord:
    patient_id: int

    calibration_days: float | None
    forecast_horizon_days: float | None
    target_day: float

    rt_start_day: float | None
    rt_started_by_t1: bool | None
    treatment_reconstructable: bool

    volume_t0_cm3: float
    volume_t1_cm3: float
    volume_t2_cm3: float

    volume_change_t0_t1: float | None
    volume_change_t1_t2: float | None

    trajectory_t0_t1: Trajectory
    trajectory_t1_t2: Trajectory

    diffusion: float
    proliferation: float

    calibration_dice: float
    calibration_volume_error: float
    calibration_loss: float

    calibration_identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool

    twin_dice: float
    twin_volume_error: float
    twin_hd95_mm: float | None
    twin_centroid_distance_mm: float | None

    persistence_dice: float
    persistence_volume_error: float

    volume_baseline_dice: float
    volume_baseline_volume_error: float

    twin_minus_persistence_dice: float
    twin_minus_volume_baseline_dice: float

    qc_warning_codes: tuple[str, ...]

    observed_outside_brain_fraction: float | None
    twin_outside_brain_fraction: float | None

    observed_component_count: int
    twin_component_count: int

    observed_largest_component_fraction: float | None
    twin_largest_component_fraction: float | None


@dataclass(frozen=True)
class CorrelationSummary:
    count: int
    pearson: float | None
    spearman: float | None


@dataclass(frozen=True)
class TrajectoryGroupSummary:
    trajectory: Trajectory
    patient_count: int
    mean_twin_dice: float | None
    mean_delta_vs_persistence: float | None
    mean_hd95_mm: float | None


@dataclass(frozen=True)
class CohortErrorSummary:
    patient_count: int

    mean_twin_dice: float | None
    median_twin_dice: float | None

    mean_delta_vs_persistence: float | None
    median_delta_vs_persistence: float | None

    mean_delta_vs_volume_baseline: float | None
    median_delta_vs_volume_baseline: float | None

    twin_better_than_persistence_count: int
    twin_equal_to_persistence_count: int
    twin_worse_than_persistence_count: int

    twin_better_than_volume_baseline_count: int
    twin_equal_to_volume_baseline_count: int
    twin_worse_than_volume_baseline_count: int

    qc_flagged_count: int
    calibration_non_identifiable_count: int
    calibration_boundary_count: int

    worst_twin_dice_patient_ids: tuple[int, ...]
    worst_delta_vs_persistence_patient_ids: tuple[int, ...]

    forecast_horizon_vs_twin_dice: CorrelationSummary
    volume_change_t1_t2_vs_twin_dice: CorrelationSummary
    calibration_dice_vs_twin_dice: CorrelationSummary

    trajectory_groups: tuple[TrajectoryGroupSummary, ...]


def relative_volume_change(
    start_volume_cm3: float,
    end_volume_cm3: float,
) -> float | None:
    if (
        not math.isfinite(start_volume_cm3)
        or not math.isfinite(end_volume_cm3)
    ):
        raise ValueError(
            "Observed tumour volumes must be finite"
        )

    if start_volume_cm3 < 0.0 or end_volume_cm3 < 0.0:
        raise ValueError(
            "Observed tumour volumes must be non-negative"
        )

    if start_volume_cm3 == 0.0:
        return None

    return (
        end_volume_cm3 - start_volume_cm3
    ) / start_volume_cm3


def classify_volume_trajectory(
    relative_change: float | None,
    *,
    stable_threshold: float,
) -> Trajectory:
    if stable_threshold < 0.0:
        raise ValueError(
            "Stable trajectory threshold must be non-negative"
        )

    if relative_change is None:
        return "unknown"

    if not math.isfinite(relative_change):
        raise ValueError(
            "Relative tumour-volume change must be finite"
        )

    if relative_change > stable_threshold:
        return "growth"

    if relative_change < -stable_threshold:
        return "regression"

    return "stable"


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None

    return float(fmean(values))


def _median(values: Sequence[float]) -> float | None:
    if not values:
        return None

    return float(median(values))


def _pearson(
    x_values: Sequence[float],
    y_values: Sequence[float],
) -> float | None:
    if len(x_values) != len(y_values):
        raise ValueError(
            "Correlation vectors must have equal length"
        )

    if len(x_values) < 2:
        return None

    mean_x = fmean(x_values)
    mean_y = fmean(y_values)

    covariance = sum(
        (x - mean_x) * (y - mean_y)
        for x, y in zip(
            x_values,
            y_values,
            strict=True,
        )
    )

    variance_x = sum(
        (x - mean_x) ** 2
        for x in x_values
    )

    variance_y = sum(
        (y - mean_y) ** 2
        for y in y_values
    )

    denominator = math.sqrt(
        variance_x * variance_y
    )

    if denominator == 0.0:
        return None

    value = covariance / denominator

    return float(
        max(-1.0, min(1.0, value))
    )


def _average_ranks(
    values: Sequence[float],
) -> list[float]:
    indexed = sorted(
        enumerate(values),
        key=lambda item: item[1],
    )

    ranks = [0.0] * len(values)
    start = 0

    while start < len(indexed):
        end = start + 1
        value = indexed[start][1]

        while (
            end < len(indexed)
            and indexed[end][1] == value
        ):
            end += 1

        average_rank = (
            (start + 1) + end
        ) / 2.0

        for position in range(start, end):
            original_index = indexed[position][0]
            ranks[original_index] = average_rank

        start = end

    return ranks


def correlation_summary(
    pairs: Sequence[tuple[float, float]],
    *,
    min_count: int,
) -> CorrelationSummary:
    if min_count < 2:
        raise ValueError(
            "Minimum correlation count must be at least 2"
        )

    finite_pairs = [
        (float(x), float(y))
        for x, y in pairs
        if math.isfinite(x) and math.isfinite(y)
    ]

    count = len(finite_pairs)

    if count < min_count:
        return CorrelationSummary(
            count=count,
            pearson=None,
            spearman=None,
        )

    x_values = [
        pair[0]
        for pair in finite_pairs
    ]

    y_values = [
        pair[1]
        for pair in finite_pairs
    ]

    return CorrelationSummary(
        count=count,
        pearson=_pearson(
            x_values,
            y_values,
        ),
        spearman=_pearson(
            _average_ranks(x_values),
            _average_ranks(y_values),
        ),
    )


def _comparison_counts(
    deltas: Sequence[float],
) -> tuple[int, int, int]:
    better = 0
    equal = 0
    worse = 0

    for delta in deltas:
        if math.isclose(
            delta,
            0.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            equal += 1
        elif delta > 0.0:
            better += 1
        else:
            worse += 1

    return (
        better,
        equal,
        worse,
    )


def _trajectory_group(
    records: Sequence[CohortPatientErrorRecord],
    trajectory: Trajectory,
) -> TrajectoryGroupSummary:
    selected = [
        record
        for record in records
        if record.trajectory_t1_t2 == trajectory
    ]

    hd95_values = [
        record.twin_hd95_mm
        for record in selected
        if record.twin_hd95_mm is not None
    ]

    return TrajectoryGroupSummary(
        trajectory=trajectory,
        patient_count=len(selected),
        mean_twin_dice=_mean(
            [
                record.twin_dice
                for record in selected
            ]
        ),
        mean_delta_vs_persistence=_mean(
            [
                record.twin_minus_persistence_dice
                for record in selected
            ]
        ),
        mean_hd95_mm=_mean(
            [
                float(value)
                for value in hd95_values
            ]
        ),
    )


def summarize_error_records(
    records: Sequence[CohortPatientErrorRecord],
    *,
    worst_patient_count: int,
    min_correlation_patients: int,
) -> CohortErrorSummary:
    if worst_patient_count < 1:
        raise ValueError(
            "worst_patient_count must be positive"
        )

    if min_correlation_patients < 2:
        raise ValueError(
            "min_correlation_patients must be at least 2"
        )

    twin_dice = [
        record.twin_dice
        for record in records
    ]

    persistence_deltas = [
        record.twin_minus_persistence_dice
        for record in records
    ]

    volume_baseline_deltas = [
        record.twin_minus_volume_baseline_dice
        for record in records
    ]

    (
        persistence_better,
        persistence_equal,
        persistence_worse,
    ) = _comparison_counts(
        persistence_deltas
    )

    (
        volume_better,
        volume_equal,
        volume_worse,
    ) = _comparison_counts(
        volume_baseline_deltas
    )

    horizon_pairs = [
        (
            record.forecast_horizon_days,
            record.twin_dice,
        )
        for record in records
        if record.forecast_horizon_days is not None
    ]

    growth_pairs = [
        (
            record.volume_change_t1_t2,
            record.twin_dice,
        )
        for record in records
        if record.volume_change_t1_t2 is not None
    ]

    calibration_pairs = [
        (
            record.calibration_dice,
            record.twin_dice,
        )
        for record in records
    ]

    worst_twin = sorted(
        records,
        key=lambda record: (
            record.twin_dice,
            record.patient_id,
        ),
    )[:worst_patient_count]

    worst_delta = sorted(
        records,
        key=lambda record: (
            record.twin_minus_persistence_dice,
            record.patient_id,
        ),
    )[:worst_patient_count]

    trajectory_order: tuple[Trajectory, ...] = (
        "growth",
        "stable",
        "regression",
        "unknown",
    )

    trajectory_groups = tuple(
        group
        for trajectory in trajectory_order
        if (
            group := _trajectory_group(
                records,
                trajectory,
            )
        ).patient_count > 0
    )

    return CohortErrorSummary(
        patient_count=len(records),
        mean_twin_dice=_mean(twin_dice),
        median_twin_dice=_median(twin_dice),
        mean_delta_vs_persistence=_mean(
            persistence_deltas
        ),
        median_delta_vs_persistence=_median(
            persistence_deltas
        ),
        mean_delta_vs_volume_baseline=_mean(
            volume_baseline_deltas
        ),
        median_delta_vs_volume_baseline=_median(
            volume_baseline_deltas
        ),
        twin_better_than_persistence_count=(
            persistence_better
        ),
        twin_equal_to_persistence_count=(
            persistence_equal
        ),
        twin_worse_than_persistence_count=(
            persistence_worse
        ),
        twin_better_than_volume_baseline_count=(
            volume_better
        ),
        twin_equal_to_volume_baseline_count=(
            volume_equal
        ),
        twin_worse_than_volume_baseline_count=(
            volume_worse
        ),
        qc_flagged_count=sum(
            bool(record.qc_warning_codes)
            for record in records
        ),
        calibration_non_identifiable_count=sum(
            not record.calibration_identifiable
            for record in records
        ),
        calibration_boundary_count=sum(
            (
                record.diffusion_at_boundary
                or record.proliferation_at_boundary
            )
            for record in records
        ),
        worst_twin_dice_patient_ids=tuple(
            record.patient_id
            for record in worst_twin
        ),
        worst_delta_vs_persistence_patient_ids=tuple(
            record.patient_id
            for record in worst_delta
        ),
        forecast_horizon_vs_twin_dice=(
            correlation_summary(
                [
                    (float(x), y)
                    for x, y in horizon_pairs
                ],
                min_count=min_correlation_patients,
            )
        ),
        volume_change_t1_t2_vs_twin_dice=(
            correlation_summary(
                [
                    (float(x), y)
                    for x, y in growth_pairs
                ],
                min_count=min_correlation_patients,
            )
        ),
        calibration_dice_vs_twin_dice=(
            correlation_summary(
                calibration_pairs,
                min_count=min_correlation_patients,
            )
        ),
        trajectory_groups=trajectory_groups,
    )
