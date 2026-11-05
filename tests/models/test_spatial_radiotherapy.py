from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.models.spatial_radiotherapy import (
    apply_spatial_pirt_fraction,
    lq_survival_field,
    normalize_cumulative_rtdose_to_gy,
    per_fraction_dose_from_cumulative_plan,
)


def test_cumulative_plan_scales_to_fraction_dose() -> None:
    cumulative = np.full((2, 2, 2), 60.0, dtype=np.float32)

    fraction = per_fraction_dose_from_cumulative_plan(
        cumulative,
        prescribed_total_dose_gy=60.0,
        dose_per_fraction_gy=2.0,
    )

    assert fraction.dtype == np.float32
    assert np.allclose(fraction, 2.0)


def test_rtdose_auto_detects_gy() -> None:
    result = normalize_cumulative_rtdose_to_gy(
        np.full((2, 2, 2), 63.0, dtype=np.float32),
        prescribed_total_dose_gy=60.0,
    )

    assert result.source_unit == "gy"
    assert result.scale_to_gy == pytest.approx(1.0)
    assert result.max_dose_gy == pytest.approx(63.0)


def test_rtdose_auto_detects_cgy() -> None:
    result = normalize_cumulative_rtdose_to_gy(
        np.full((2, 2, 2), 6300.0, dtype=np.float32),
        prescribed_total_dose_gy=60.0,
    )

    assert result.source_unit == "cgy"
    assert result.scale_to_gy == pytest.approx(0.01)
    assert result.max_dose_gy == pytest.approx(63.0)


def test_rtdose_auto_fails_closed_for_unexpected_scale() -> None:
    with pytest.raises(ValueError, match="infer RTDOSE unit"):
        normalize_cumulative_rtdose_to_gy(
            np.full((2, 2, 2), 6.0, dtype=np.float32),
            prescribed_total_dose_gy=60.0,
        )


def test_lq_survival_field_is_spatial() -> None:
    dose = np.zeros((2, 2, 2), dtype=np.float32)
    dose[1, 1, 1] = 2.0

    survival = lq_survival_field(
        dose,
        alpha_per_gy=0.1,
        beta_per_gy2=0.01,
    )

    assert survival[0, 0, 0] == pytest.approx(1.0)
    assert survival[1, 1, 1] == pytest.approx(
        np.exp(-(0.1 * 2.0 + 0.01 * 4.0)),
        rel=1e-6,
    )


def test_spatial_pirt_only_changes_irradiated_voxel() -> None:
    field = np.full((2, 2, 2), 0.5, dtype=np.float32)
    survival = np.ones_like(field)
    survival[1, 1, 1] = 0.5

    result = apply_spatial_pirt_fraction(
        field,
        survival_fraction=survival,
    )

    assert result[0, 0, 0] == pytest.approx(0.5)
    assert result[1, 1, 1] == pytest.approx(0.375)


def test_fraction_dose_rejects_invalid_prescription() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        per_fraction_dose_from_cumulative_plan(
            np.ones((2, 2, 2), dtype=np.float32),
            prescribed_total_dose_gy=2.0,
            dose_per_fraction_gy=3.0,
        )
