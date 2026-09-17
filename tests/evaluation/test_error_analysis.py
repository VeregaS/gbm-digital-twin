from __future__ import annotations

import pytest

from gbm_twin.evaluation.error_analysis import (
    CohortPatientErrorRecord,
    classify_volume_trajectory,
    correlation_summary,
    relative_volume_change,
    summarize_error_records,
)


def make_record(
    *,
    patient_id: int,
    horizon: float,
    change_t1_t2: float,
    twin_dice: float,
    persistence_dice: float,
    volume_baseline_dice: float,
    calibration_dice: float,
    identifiable: bool = True,
    at_boundary: bool = False,
    qc_warning: bool = False,
) -> CohortPatientErrorRecord:
    return CohortPatientErrorRecord(
        patient_id=patient_id,
        calibration_days=60.0,
        forecast_horizon_days=horizon,
        target_day=120.0,
        rt_start_day=10.0,
        rt_started_by_t1=True,
        treatment_reconstructable=True,
        volume_t0_cm3=10.0,
        volume_t1_cm3=12.0,
        volume_t2_cm3=(
            12.0 * (1.0 + change_t1_t2)
        ),
        volume_change_t0_t1=0.2,
        volume_change_t1_t2=change_t1_t2,
        trajectory_t0_t1="growth",
        trajectory_t1_t2=(
            classify_volume_trajectory(
                change_t1_t2,
                stable_threshold=0.10,
            )
        ),
        diffusion=0.015,
        proliferation=0.035,
        calibration_dice=calibration_dice,
        calibration_volume_error=0.1,
        calibration_loss=0.2,
        calibration_identifiable=identifiable,
        diffusion_at_boundary=at_boundary,
        proliferation_at_boundary=False,
        twin_dice=twin_dice,
        twin_volume_error=0.15,
        twin_hd95_mm=5.0,
        twin_centroid_distance_mm=3.0,
        persistence_dice=persistence_dice,
        persistence_volume_error=0.2,
        volume_baseline_dice=volume_baseline_dice,
        volume_baseline_volume_error=0.18,
        twin_minus_persistence_dice=(
            twin_dice - persistence_dice
        ),
        twin_minus_volume_baseline_dice=(
            twin_dice - volume_baseline_dice
        ),
        qc_warning_codes=(
            ("observed_fragmented",)
            if qc_warning
            else ()
        ),
        observed_outside_brain_fraction=0.0,
        twin_outside_brain_fraction=0.0,
        observed_component_count=1,
        twin_component_count=1,
        observed_largest_component_fraction=1.0,
        twin_largest_component_fraction=1.0,
    )


def test_relative_volume_change_and_trajectory() -> None:
    assert relative_volume_change(
        10.0,
        12.0,
    ) == pytest.approx(0.2)

    assert relative_volume_change(
        0.0,
        12.0,
    ) is None

    assert classify_volume_trajectory(
        0.11,
        stable_threshold=0.10,
    ) == "growth"

    assert classify_volume_trajectory(
        -0.11,
        stable_threshold=0.10,
    ) == "regression"

    assert classify_volume_trajectory(
        0.05,
        stable_threshold=0.10,
    ) == "stable"

    assert classify_volume_trajectory(
        None,
        stable_threshold=0.10,
    ) == "unknown"


def test_correlation_summary_reports_pearson_and_spearman() -> None:
    result = correlation_summary(
        [
            (1.0, 2.0),
            (2.0, 4.0),
            (3.0, 6.0),
        ],
        min_count=3,
    )

    assert result.count == 3
    assert result.pearson == pytest.approx(1.0)
    assert result.spearman == pytest.approx(1.0)


def test_correlation_summary_requires_enough_pairs() -> None:
    result = correlation_summary(
        [
            (1.0, 2.0),
            (2.0, 3.0),
        ],
        min_count=3,
    )

    assert result.count == 2
    assert result.pearson is None
    assert result.spearman is None


def test_summarize_error_records_exposes_failure_modes() -> None:
    records = [
        make_record(
            patient_id=1,
            horizon=30.0,
            change_t1_t2=0.05,
            twin_dice=0.90,
            persistence_dice=0.80,
            volume_baseline_dice=0.82,
            calibration_dice=0.95,
        ),
        make_record(
            patient_id=2,
            horizon=60.0,
            change_t1_t2=0.40,
            twin_dice=0.70,
            persistence_dice=0.72,
            volume_baseline_dice=0.68,
            calibration_dice=0.80,
            identifiable=False,
            qc_warning=True,
        ),
        make_record(
            patient_id=3,
            horizon=90.0,
            change_t1_t2=-0.30,
            twin_dice=0.50,
            persistence_dice=0.60,
            volume_baseline_dice=0.55,
            calibration_dice=0.65,
            at_boundary=True,
        ),
    ]

    summary = summarize_error_records(
        records,
        worst_patient_count=2,
        min_correlation_patients=3,
    )

    assert summary.patient_count == 3
    assert summary.mean_twin_dice == pytest.approx(0.7)
    assert summary.median_twin_dice == pytest.approx(0.7)

    assert summary.twin_better_than_persistence_count == 1
    assert summary.twin_equal_to_persistence_count == 0
    assert summary.twin_worse_than_persistence_count == 2

    assert summary.qc_flagged_count == 1
    assert summary.calibration_non_identifiable_count == 1
    assert summary.calibration_boundary_count == 1

    assert summary.worst_twin_dice_patient_ids == (
        3,
        2,
    )

    assert summary.worst_delta_vs_persistence_patient_ids == (
        3,
        2,
    )

    assert (
        summary.forecast_horizon_vs_twin_dice.pearson
        == pytest.approx(-1.0)
    )

    trajectories = {
        group.trajectory: group.patient_count
        for group in summary.trajectory_groups
    }

    assert trajectories == {
        "growth": 1,
        "stable": 1,
        "regression": 1,
    }
