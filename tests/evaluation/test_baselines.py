import math

import numpy as np

from gbm_twin.evaluation.baselines import expand_mask_to_volume, extrapolate_volume


def test_extrapolate_volume_constant_growth() -> None:
    predicted = extrapolate_volume(
        10.0,
        20.0,
        dt01_days=10,
        dt12_days=10,
    )

    assert math.isclose(predicted, 40.0)
    
def test_expand_mask_to_volume() -> None:
    mask = np.zeros((20, 20, 20), dtype=bool)
    mask[9:11, 9:11, 9:11] = True

    result = expand_mask_to_volume(
        mask,
        target_volume_cm3=0.016,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.count_nonzero(result) == 16
    assert np.all(result[mask])