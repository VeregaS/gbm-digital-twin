import numpy as np
import pytest

from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
    signed_distance_from_mask,
)


def test_signed_distance_is_positive_inside() -> None:
    mask = np.zeros(
        (7, 7, 7),
        dtype=bool,
    )

    mask[
        2:5,
        2:5,
        2:5,
    ] = True

    distance = signed_distance_from_mask(
        mask,
        spacing=(2.0, 2.0, 2.0),
    )

    assert distance[
        3,
        3,
        3,
    ] > 0.0

    assert distance[
        0,
        0,
        0,
    ] < 0.0


def test_latent_state_is_bounded() -> None:
    gtv = np.zeros(
        (7, 7, 7),
        dtype=bool,
    )

    gtv[
        2:5,
        2:5,
        2:5,
    ] = True

    brain = np.ones_like(
        gtv
    )

    field = latent_state_from_gtv(
        gtv,
        brain,
        spacing=(2.0, 2.0, 2.0),
    )

    assert np.all(
        field >= 0.0
    )

    assert np.all(
        field <= 1.0
    )


def test_half_threshold_reconstructs_gtv() -> None:
    gtv = np.zeros(
        (9, 9, 9),
        dtype=bool,
    )

    gtv[
        3:6,
        3:6,
        3:6,
    ] = True

    brain = np.ones_like(
        gtv
    )

    field = latent_state_from_gtv(
        gtv,
        brain,
        spacing=(2.0, 2.0, 2.0),
        parameters=LatentStateParameters(
            transition_width_mm=4.0,
        ),
    )

    reconstructed = (
        field >= 0.5
    )

    assert np.array_equal(
        reconstructed,
        gtv,
    )


def test_latent_state_has_infiltrating_tail() -> None:
    gtv = np.zeros(
        (9, 9, 9),
        dtype=bool,
    )

    gtv[
        4,
        4,
        4,
    ] = True

    brain = np.ones_like(
        gtv
    )

    field = latent_state_from_gtv(
        gtv,
        brain,
        spacing=(2.0, 2.0, 2.0),
    )

    assert (
        field[
            4,
            4,
            5,
        ]
        > 0.0
    )

    assert (
        field[
            4,
            4,
            5,
        ]
        < 0.5
    )


def test_latent_state_is_zero_outside_brain() -> None:
    gtv = np.zeros(
        (7, 7, 7),
        dtype=bool,
    )

    gtv[
        3,
        3,
        3,
    ] = True

    brain = np.zeros_like(
        gtv
    )

    brain[
        2:5,
        2:5,
        2:5,
    ] = True

    field = latent_state_from_gtv(
        gtv,
        brain,
        spacing=(2.0, 2.0, 2.0),
    )

    assert field[
        0,
        0,
        0,
    ] == 0.0


def test_rejects_nonpositive_transition_width() -> None:
    with pytest.raises(
        ValueError,
        match="transition_width_mm",
    ):
        LatentStateParameters(
            transition_width_mm=0.0,
        )