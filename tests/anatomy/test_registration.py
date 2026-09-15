import numpy as np
import SimpleITK as sitk

from gbm_twin.anatomy.registration import (
    RegistrationConfig,
    _initial_rigid_transform,
    evaluate_registration_quality,
)


def _mask_from_array(
    array: np.ndarray,
    *,
    origin: tuple[
        float,
        float,
        float,
    ],
) -> sitk.Image:
    image = sitk.GetImageFromArray(
        np.transpose(
            array.astype(
                np.uint8
            ),
            (
                2,
                1,
                0,
            ),
        )
    )

    image.SetSpacing(
        (
            1.0,
            1.0,
            1.0,
        )
    )

    image.SetOrigin(
        origin
    )

    return image


def test_centroid_initialization() -> None:
    data = np.zeros(
        (
            40,
            40,
            40,
        ),
        dtype=np.uint8,
    )

    data[
        10:30,
        10:30,
        10:30,
    ] = 1

    fixed = _mask_from_array(
        data,
        origin=(
            100.0,
            50.0,
            -20.0,
        ),
    )

    moving = _mask_from_array(
        data,
        origin=(
            -80.0,
            -40.0,
            60.0,
        ),
    )

    transform = (
        _initial_rigid_transform(
            fixed_mask=fixed,
            moving_mask=moving,
        )
    )

    fixed_center = np.asarray(
        (
            119.5,
            69.5,
            -0.5,
        )
    )

    transformed = np.asarray(
        transform.TransformPoint(
            tuple(
                fixed_center
            )
        )
    )

    expected = np.asarray(
        (
            -60.5,
            -20.5,
            79.5,
        )
    )

    assert np.allclose(
        transformed,
        expected,
    )


def test_registration_quality_passes() -> None:
    fixed = np.zeros(
        (
            20,
            20,
            20,
        ),
        dtype=bool,
    )

    fixed[
        3:17,
        3:17,
        3:17,
    ] = True

    labels = np.zeros(
        fixed.shape,
        dtype=np.uint16,
    )

    labels[
        6:14,
        6:14,
        6:14,
    ] = 1

    quality = (
        evaluate_registration_quality(
            fixed_brain_mask=fixed,
            registered_template_mask=(
                fixed
            ),
            registered_labels=(
                labels
            ),
            config=(
                RegistrationConfig()
            ),
        )
    )

    assert (
        quality.status
        == "pass"
    )

    assert (
        quality.brain_dice
        == 1.0
    )

    assert (
        quality
        .labeled_inside_brain_fraction
        == 1.0
    )


def test_registration_quality_warns() -> None:
    fixed = np.zeros(
        (
            20,
            20,
            20,
        ),
        dtype=bool,
    )

    registered = np.zeros_like(
        fixed
    )

    fixed[
        2:18,
        2:18,
        2:18,
    ] = True

    registered[
        4:20,
        2:18,
        2:18,
    ] = True

    labels = np.zeros(
        fixed.shape,
        dtype=np.uint16,
    )

    labels[
        5:17,
        4:16,
        4:16,
    ] = 1

    quality = (
        evaluate_registration_quality(
            fixed_brain_mask=fixed,
            registered_template_mask=(
                registered
            ),
            registered_labels=(
                labels
            ),
            config=(
                RegistrationConfig()
            ),
        )
    )

    assert quality.status in {
        "pass",
        "warn",
    }


def test_registration_quality_fails() -> None:
    fixed = np.zeros(
        (
            20,
            20,
            20,
        ),
        dtype=bool,
    )

    registered = np.zeros_like(
        fixed
    )

    fixed[
        1:7,
        1:7,
        1:7,
    ] = True

    registered[
        13:19,
        13:19,
        13:19,
    ] = True

    quality = (
        evaluate_registration_quality(
            fixed_brain_mask=fixed,
            registered_template_mask=(
                registered
            ),
            registered_labels=(
                registered.astype(
                    np.uint16
                )
            ),
            config=(
                RegistrationConfig()
            ),
        )
    )

    assert (
        quality.status
        == "fail"
    )