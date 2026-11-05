from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.models.observation import (
    MRIDetectionObservationParameters,
    latent_density_from_mri_detection,
)


def test_enhancing_detection_builds_bounded_latent_density() -> None:
    enhancing = np.zeros((9, 9, 9), dtype=bool)
    enhancing[3:6, 3:6, 3:6] = True
    brain = np.ones_like(enhancing)

    field = latent_density_from_mri_detection(
        enhancing,
        brain,
        spacing=(1.0, 1.0, 1.0),
    )

    assert field.dtype == np.float32
    assert np.all(field >= 0.0)
    assert np.all(field <= 1.0)
    assert float(field[4, 4, 4]) > 0.8
    assert float(field[0, 0, 0]) < float(field[4, 4, 4])


def test_infiltrative_detection_raises_density_outside_enhancing_core() -> None:
    # The infiltrative surface represents a lower-density observation farther
    # from the enhancing core. With the default 4 mm transition width it must
    # be spatially separated enough to add information beyond the enhancing
    # profile's own tail.
    enhancing = np.zeros((31, 31, 31), dtype=bool)
    enhancing[15, 15, 15] = True

    infiltrative = np.zeros_like(enhancing)
    infiltrative[2:29, 2:29, 2:29] = True

    brain = np.ones_like(enhancing)

    without_infiltrative = latent_density_from_mri_detection(
        enhancing,
        brain,
        spacing=(1.0, 1.0, 1.0),
    )
    with_infiltrative = latent_density_from_mri_detection(
        enhancing,
        brain,
        spacing=(1.0, 1.0, 1.0),
        infiltrative_mask=infiltrative,
    )

    shell_voxel = (2, 15, 15)

    assert (
        with_infiltrative[shell_voxel]
        > without_infiltrative[shell_voxel]
    )
    assert with_infiltrative[15, 15, 15] >= 0.8


def test_enhancing_region_must_be_inside_infiltrative_region() -> None:
    enhancing = np.zeros((5, 5, 5), dtype=bool)
    enhancing[2, 2, 2] = True

    infiltrative = np.zeros_like(enhancing)
    infiltrative[1, 1, 1] = True

    with pytest.raises(
        ValueError,
        match="contained",
    ):
        latent_density_from_mri_detection(
            enhancing,
            np.ones_like(enhancing),
            spacing=(1.0, 1.0, 1.0),
            infiltrative_mask=infiltrative,
        )


def test_observation_parameters_require_ordered_thresholds() -> None:
    with pytest.raises(
        ValueError,
        match="lower",
    ):
        MRIDetectionObservationParameters(
            enhancing_threshold=0.2,
            infiltrative_threshold=0.3,
        )
