from __future__ import annotations

import pytest

from gbm_twin.evaluation.experiment_comparison import (
    compare_cohort_analyses,
)


def _row(
    patient_id: int,
    *,
    twin_dice: float,
    delta_vs_persistence: float,
    calibration_dice: float,
    diffusion: float,
    proliferation: float,
    identifiable: bool,
    diffusion_boundary: bool,
    proliferation_boundary: bool,
) -> dict[str, object]:
    return {
        "patient_id": patient_id,
        "twin_dice": twin_dice,
        "twin_minus_persistence_dice": delta_vs_persistence,
        "calibration_dice": calibration_dice,
        "diffusion": diffusion,
        "proliferation": proliferation,
        "calibration_identifiable": identifiable,
        "diffusion_at_boundary": diffusion_boundary,
        "proliferation_at_boundary": proliferation_boundary,
    }


def _payload(
    rows: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "v2_cohort_error_analysis",
        "sealed": True,
        "patients": rows,
    }


def test_compare_cohort_analyses_reports_patient_and_summary_deltas() -> None:
    baseline = _payload(
        [
            _row(
                8,
                twin_dice=0.60,
                delta_vs_persistence=-0.10,
                calibration_dice=0.70,
                diffusion=0.0375,
                proliferation=0.01,
                identifiable=False,
                diffusion_boundary=True,
                proliferation_boundary=False,
            ),
            _row(
                25,
                twin_dice=0.80,
                delta_vs_persistence=0.00,
                calibration_dice=0.85,
                diffusion=0.01,
                proliferation=0.00,
                identifiable=True,
                diffusion_boundary=False,
                proliferation_boundary=True,
            ),
        ]
    )

    candidate = _payload(
        [
            _row(
                8,
                twin_dice=0.70,
                delta_vs_persistence=0.00,
                calibration_dice=0.75,
                diffusion=0.06,
                proliferation=0.01,
                identifiable=True,
                diffusion_boundary=False,
                proliferation_boundary=False,
            ),
            _row(
                25,
                twin_dice=0.78,
                delta_vs_persistence=-0.02,
                calibration_dice=0.86,
                diffusion=0.0125,
                proliferation=0.00,
                identifiable=True,
                diffusion_boundary=False,
                proliferation_boundary=True,
            ),
        ]
    )

    result = compare_cohort_analyses(
        baseline,
        candidate,
    )

    assert result.patient_count == 2
    assert result.mean_twin_dice_delta == pytest.approx(0.04)
    assert result.median_twin_dice_delta == pytest.approx(0.04)
    assert result.improved_patient_count == 1
    assert result.equal_patient_count == 0
    assert result.degraded_patient_count == 1
    assert result.mean_delta_vs_persistence_change == pytest.approx(0.04)
    assert result.baseline_boundary_patient_count == 2
    assert result.candidate_boundary_patient_count == 1
    assert result.baseline_non_identifiable_count == 1
    assert result.candidate_non_identifiable_count == 0

    first = result.patients[0]
    assert first.patient_id == 8
    assert first.twin_dice_delta == pytest.approx(0.10)
    assert first.calibration_dice_delta == pytest.approx(0.05)
    assert first.baseline_diffusion == pytest.approx(0.0375)
    assert first.candidate_diffusion == pytest.approx(0.06)


def test_compare_cohort_analyses_rejects_different_patient_sets() -> None:
    baseline = _payload(
        [
            _row(
                8,
                twin_dice=0.6,
                delta_vs_persistence=0.0,
                calibration_dice=0.7,
                diffusion=0.01,
                proliferation=0.01,
                identifiable=True,
                diffusion_boundary=False,
                proliferation_boundary=False,
            )
        ]
    )

    candidate = _payload(
        [
            _row(
                25,
                twin_dice=0.6,
                delta_vs_persistence=0.0,
                calibration_dice=0.7,
                diffusion=0.01,
                proliferation=0.01,
                identifiable=True,
                diffusion_boundary=False,
                proliferation_boundary=False,
            )
        ]
    )

    with pytest.raises(
        ValueError,
        match="different patients",
    ):
        compare_cohort_analyses(
            baseline,
            candidate,
        )
