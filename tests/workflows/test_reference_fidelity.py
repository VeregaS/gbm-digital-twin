from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.workflows.reference_fidelity import (
    _adc_eligible_patient_ids,
    _restore_prediction,
    _roi_slices,
)


def test_roi_slices_cover_support_with_padding() -> None:
    support = np.zeros((12, 14, 16), dtype=bool)
    support[4:7, 5:9, 6:10] = True

    roi = _roi_slices(support, padding_voxels=2)

    assert roi == (
        slice(2, 9),
        slice(3, 11),
        slice(4, 12),
    )
    assert np.all(support[roi])


def test_roi_slices_clip_padding_to_volume_bounds() -> None:
    support = np.zeros((8, 8, 8), dtype=bool)
    support[0:3, 5:8, 2:5] = True

    roi = _roi_slices(support, padding_voxels=4)

    assert roi == (
        slice(0, 7),
        slice(1, 8),
        slice(0, 8),
    )


def test_roi_slices_reject_empty_support() -> None:
    with pytest.raises(ValueError, match="at least one voxel"):
        _roi_slices(
            np.zeros((5, 5, 5), dtype=bool),
            padding_voxels=1,
        )


def test_restore_prediction_places_crop_on_full_grid() -> None:
    roi = (slice(1, 4), slice(2, 5), slice(0, 3))
    prediction = np.ones((3, 3, 3), dtype=np.float32)

    restored = _restore_prediction(
        prediction,
        full_shape=(6, 7, 5),
        roi=roi,
    )

    assert restored.shape == (6, 7, 5)
    assert np.all(restored[roi] == 1.0)
    assert np.count_nonzero(restored) == prediction.size


def test_adc_eligibility_requires_t0_and_t1_only() -> None:
    rows = {
        25: {"t0_adc": True, "t1_adc": True, "t2_adc": True},
        45: {"t0_adc": True, "t1_adc": True, "t2_adc": False},
        65: {"t0_adc": True, "t1_adc": False, "t2_adc": True},
        70: {"t0_adc": False, "t1_adc": True, "t2_adc": True},
    }

    eligible = _adc_eligible_patient_ids(
        (25, 45, 65, 70),
        rows,
    )

    assert eligible == (25, 45)
