from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.reference.tumortwin_cellularity import (
    TUMORTWIN_NONENHANCING_CELLULARITY,
    adc_water_reference,
    tumortwin_adc_to_cellularity,
)


@pytest.mark.parametrize(
    ("maximum", "expected"),
    [
        (3001.0, 3000.0),
        (800.0, 300.0),
        (80.0, 30.0),
        (8.0, 3.0),
        (0.8, 0.3),
        (0.08, 0.03),
        (0.008, 0.003),
        (0.0008, 3.0),
    ],
)
def test_adc_water_reference_matches_upstream_scale_heuristic(
    maximum: float,
    expected: float,
) -> None:
    adc = np.array([[[0.0, maximum]]], dtype=np.float32)

    assert adc_water_reference(adc) == expected


def test_adc_cellularity_uses_enhancing_roi_only_by_default() -> None:
    adc = np.full((3, 3, 3), 1500.0, dtype=np.float32)
    enhancing = np.zeros((3, 3, 3), dtype=bool)
    enhancing[1, 1, 1] = True

    result = tumortwin_adc_to_cellularity(adc, enhancing)

    assert result[1, 1, 1] == pytest.approx(0.5)
    assert np.count_nonzero(result) == 1


def test_adc_cellularity_assigns_explicit_nonenhancing_density() -> None:
    adc = np.full((3, 3, 3), 1500.0, dtype=np.float32)
    enhancing = np.zeros((3, 3, 3), dtype=bool)
    nonenhancing = np.zeros((3, 3, 3), dtype=bool)
    enhancing[1, 1, 1] = True
    nonenhancing[0, 0, 0] = True

    result = tumortwin_adc_to_cellularity(
        adc,
        enhancing,
        nonenhancing,
    )

    assert result[1, 1, 1] == pytest.approx(0.5)
    assert result[0, 0, 0] == pytest.approx(
        TUMORTWIN_NONENHANCING_CELLULARITY
    )


def test_adc_cellularity_rejects_nonfinite_values() -> None:
    adc = np.ones((2, 2, 2), dtype=np.float32)
    adc[0, 0, 0] = np.nan
    enhancing = np.ones((2, 2, 2), dtype=bool)

    with pytest.raises(ValueError, match="finite"):
        tumortwin_adc_to_cellularity(adc, enhancing)
