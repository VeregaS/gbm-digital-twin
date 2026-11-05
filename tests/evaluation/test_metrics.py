from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from gbm_twin.data.nifti import (
    NiftiVolume,
)
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    mask_volume_cm3,
    relative_volume_error,
)


def test_mask_volume_cm3() -> None:
    data = np.zeros(
        (10, 10, 10),
        dtype=np.uint8,
    )

    data[
        :5,
        :5,
        :4,
    ] = 1

    volume = NiftiVolume(
        path=Path(
            "test.nii.gz"
        ),
        data=data,
        affine=np.eye(
            4,
            dtype=np.float64,
        ),
        spacing=(
            1.0,
            1.0,
            1.0,
        ),
    )

    assert (
        mask_volume_cm3(
            volume
        )
        == 0.1
    )


def test_dice_identical_masks() -> None:
    mask = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    mask[
        2,
        2,
        2,
    ] = True

    assert (
        dice_score(
            mask,
            mask,
        )
        == 1.0
    )


def test_relative_volume_error() -> None:
    observed = np.zeros(
        (10, 10, 10),
        dtype=bool,
    )

    predicted = np.zeros_like(
        observed
    )

    observed.flat[:100] = True
    predicted.flat[:120] = True

    assert np.isclose(
        relative_volume_error(
            predicted,
            observed,
        ),
        0.2,
    )


def test_centroid_distance_identical_masks_is_zero(
) -> None:
    mask = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    mask[
        2,
        2,
        2,
    ] = True

    result = centroid_distance_mm(
        mask,
        mask,
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )

    assert result == 0.0


def test_centroid_distance_uses_physical_spacing(
) -> None:
    first = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    second = np.zeros_like(
        first
    )

    first[
        1,
        2,
        2,
    ] = True

    second[
        2,
        2,
        2,
    ] = True

    result = centroid_distance_mm(
        first,
        second,
        spacing=(
            2.5,
            1.0,
            1.0,
        ),
    )

    assert result is not None

    assert np.isclose(
        result,
        2.5,
    )


def test_hausdorff95_identical_masks_is_zero(
) -> None:
    mask = np.zeros(
        (7, 7, 7),
        dtype=bool,
    )

    mask[
        2:5,
        2:5,
        2:5,
    ] = True

    result = hausdorff95_mm(
        mask,
        mask,
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )

    assert result is not None

    assert np.isclose(
        result,
        0.0,
    )


def test_hausdorff95_uses_physical_spacing(
) -> None:
    first = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    second = np.zeros_like(
        first
    )

    first[
        1,
        2,
        2,
    ] = True

    second[
        2,
        2,
        2,
    ] = True

    result = hausdorff95_mm(
        first,
        second,
        spacing=(
            3.0,
            1.0,
            1.0,
        ),
    )

    assert result is not None

    assert np.isclose(
        result,
        3.0,
    )


@pytest.mark.parametrize(
    "metric",
    (
        centroid_distance_mm,
        hausdorff95_mm,
    ),
)
def test_spatial_metric_returns_none_for_empty_mask(
    metric,
) -> None:
    empty = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    nonempty = np.zeros_like(
        empty
    )

    nonempty[
        2,
        2,
        2,
    ] = True

    result = metric(
        empty,
        nonempty,
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )

    assert result is None


def test_spatial_metric_rejects_shape_mismatch(
) -> None:
    first = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    second = np.zeros(
        (6, 5, 5),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="Shape mismatch",
    ):
        hausdorff95_mm(
            first,
            second,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
        )


def test_spatial_metric_rejects_invalid_spacing(
) -> None:
    mask = np.ones(
        (3, 3, 3),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match=(
            "finite and positive"
        ),
    ):
        centroid_distance_mm(
            mask,
            mask,
            spacing=(
                2.0,
                0.0,
                2.0,
            ),
        )