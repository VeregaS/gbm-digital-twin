import math

import numpy as np

from gbm_twin.evaluation.baselines import (
    extrapolate_volume,
    resize_mask_to_volume,
)


def test_extrapolate_volume_constant_growth() -> None:
    predicted = extrapolate_volume(
        10.0,
        20.0,
        dt01_days=10,
        dt12_days=10,
    )

    assert math.isclose(
        predicted,
        40.0,
    )


def test_resize_mask_expands_to_target_volume() -> None:
    mask = np.zeros(
        (20, 20, 20),
        dtype=bool,
    )

    mask[
        9:11,
        9:11,
        9:11,
    ] = True

    result = resize_mask_to_volume(
        mask,
        target_volume_cm3=0.016,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.count_nonzero(
        result
    ) == 16

    assert np.all(
        result[mask]
    )


def test_resize_mask_shrinks_to_target_volume() -> None:
    mask = np.zeros(
        (20, 20, 20),
        dtype=bool,
    )

    mask[
        8:12,
        8:12,
        8:12,
    ] = True

    result = resize_mask_to_volume(
        mask,
        target_volume_cm3=0.032,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.count_nonzero(
        result
    ) == 32

    assert np.all(
        result <= mask
    )


def test_resize_mask_preserves_same_volume() -> None:
    mask = np.zeros(
        (10, 10, 10),
        dtype=bool,
    )

    mask[
        4:6,
        4:6,
        4:6,
    ] = True

    result = resize_mask_to_volume(
        mask,
        target_volume_cm3=0.008,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.array_equal(
        result,
        mask,
    )