import numpy as np
import pytest

from gbm_twin.models.domain_crop import (
    DomainCrop,
)


def test_domain_crop_finds_bounding_box() -> None:
    mask = np.zeros(
        (10, 12, 14),
        dtype=bool,
    )

    mask[
        2:8,
        3:10,
        4:11,
    ] = True

    crop = DomainCrop.from_mask(
        mask
    )

    assert crop.original_shape == (
        10,
        12,
        14,
    )

    assert crop.cropped_shape == (
        6,
        7,
        7,
    )


def test_domain_crop_crop_and_restore() -> None:
    array = np.zeros(
        (8, 9, 10),
        dtype=np.float32,
    )

    array[
        2:6,
        3:8,
        1:9,
    ] = 0.5

    mask = (
        array
        > 0
    )

    crop = DomainCrop.from_mask(
        mask
    )

    cropped = crop.crop(
        array
    )

    restored = crop.restore(
        cropped
    )

    np.testing.assert_array_equal(
        restored,
        array,
    )


def test_domain_crop_rejects_empty_mask() -> None:
    mask = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="empty",
    ):
        DomainCrop.from_mask(
            mask
        )