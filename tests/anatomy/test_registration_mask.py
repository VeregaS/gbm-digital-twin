import numpy as np

from gbm_twin.anatomy.registration_mask import (
    clean_registration_mask,
)


def test_registration_mask_removes_island() -> None:
    mask = np.zeros(
        (
            30,
            30,
            30,
        ),
        dtype=bool,
    )

    mask[
        5:25,
        5:25,
        5:25,
    ] = True

    mask[
        1:3,
        1:3,
        1:3,
    ] = True

    result = (
        clean_registration_mask(
            mask
        )
    )

    assert (
        result.report
        .component_count
        == 2
    )

    assert not np.any(
        result.mask[
            1:3,
            1:3,
            1:3,
        ]
    )

    assert np.all(
        result.mask[
            8:20,
            8:20,
            8:20,
        ]
    )


def test_registration_mask_fills_hole() -> None:
    mask = np.zeros(
        (
            24,
            24,
            24,
        ),
        dtype=bool,
    )

    mask[
        4:20,
        4:20,
        4:20,
    ] = True

    mask[
        10:14,
        10:14,
        10:14,
    ] = False

    result = (
        clean_registration_mask(
            mask
        )
    )

    assert np.all(
        result.mask[
            10:14,
            10:14,
            10:14,
        ]
    )


def test_registration_mask_rejects_empty() -> None:
    mask = np.zeros(
        (
            10,
            10,
            10,
        ),
        dtype=bool,
    )

    try:
        clean_registration_mask(
            mask
        )

    except ValueError as exc:
        assert (
            "empty"
            in str(exc).lower()
        )

    else:
        raise AssertionError(
            "Expected ValueError"
        )