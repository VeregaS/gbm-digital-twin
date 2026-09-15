from pathlib import Path

import numpy as np
import SimpleITK as sitk
from PIL import Image

from gbm_twin.anatomy.source_qc import (
    render_anatomy_source_qc,
)


def _write_sitk_image(
    *,
    array_xyz: np.ndarray,
    path: Path,
    pixel_id: int,
) -> None:
    array_zyx = np.transpose(
        array_xyz,
        (
            2,
            1,
            0,
        ),
    )

    image = sitk.GetImageFromArray(
        array_zyx
    )

    image.SetSpacing(
        (
            1.0,
            1.0,
            1.0,
        )
    )

    image.SetOrigin(
        (
            -20.0,
            -30.0,
            -10.0,
        )
    )

    image = sitk.Cast(
        image,
        pixel_id,
    )

    sitk.WriteImage(
        image,
        str(path),
        True,
    )


def test_render_anatomy_source_qc(
    tmp_path: Path,
) -> None:
    patient_shape = (
        40,
        42,
        36,
    )

    patient_t1 = np.zeros(
        patient_shape,
        dtype=np.float32,
    )

    patient_brain = np.zeros(
        patient_shape,
        dtype=np.uint8,
    )

    patient_brain[
        5:35,
        6:36,
        4:32,
    ] = 1

    x = np.linspace(
        0.0,
        1.0,
        patient_shape[0],
        dtype=np.float32,
    )

    y = np.linspace(
        0.0,
        1.0,
        patient_shape[1],
        dtype=np.float32,
    )

    z = np.linspace(
        0.0,
        1.0,
        patient_shape[2],
        dtype=np.float32,
    )

    patient_t1[:] = (
        x[
            :,
            None,
            None,
        ]
        + y[
            None,
            :,
            None,
        ]
        + z[
            None,
            None,
            :,
        ]
    )

    patient_t1[
        patient_brain == 0
    ] = 0.0

    atlas_shape = (
        48,
        50,
        44,
    )

    atlas_t1 = np.zeros(
        atlas_shape,
        dtype=np.float32,
    )

    atlas_brain = np.zeros(
        atlas_shape,
        dtype=np.uint8,
    )

    atlas_labels = np.zeros(
        atlas_shape,
        dtype=np.uint16,
    )

    atlas_brain[
        6:42,
        7:43,
        5:39,
    ] = 1

    atlas_labels[
        12:36,
        13:37,
        10:34,
    ] = 3

    atlas_t1[
        atlas_brain > 0
    ] = 100.0

    template_path = (
        tmp_path
        / "template_t1.nii.gz"
    )

    brain_mask_path = (
        tmp_path
        / "template_brain_mask.nii.gz"
    )

    labels_path = (
        tmp_path
        / "template_labels.nii.gz"
    )

    _write_sitk_image(
        array_xyz=(
            atlas_t1
        ),
        path=(
            template_path
        ),
        pixel_id=(
            sitk.sitkFloat32
        ),
    )

    _write_sitk_image(
        array_xyz=(
            atlas_brain
        ),
        path=(
            brain_mask_path
        ),
        pixel_id=(
            sitk.sitkUInt8
        ),
    )

    _write_sitk_image(
        array_xyz=(
            atlas_labels
        ),
        path=(
            labels_path
        ),
        pixel_id=(
            sitk.sitkUInt16
        ),
    )

    output_dir = (
        tmp_path
        / "qc"
    )

    result = (
        render_anatomy_source_qc(
            patient_t1=(
                patient_t1
            ),
            patient_brain_mask=(
                patient_brain
            ),
            atlas_template_path=(
                template_path
            ),
            atlas_brain_mask_path=(
                brain_mask_path
            ),
            atlas_labels_path=(
                labels_path
            ),
            output_dir=(
                output_dir
            ),
            patient_id=108,
            timepoint_name="t1",
            tile_size=128,
        )
    )

    assert (
        result
        .patient_image_path
        .is_file()
    )

    assert (
        result
        .atlas_image_path
        .is_file()
    )

    assert (
        result
        .report_path
        .is_file()
    )

    assert (
        result.metrics
        .patient_brain_voxels
        > 0
    )

    assert (
        result.metrics
        .atlas_brain_voxels
        > 0
    )

    assert (
        result.metrics
        .atlas_label_voxels
        > 0
    )

    assert (
        result.metrics
        .atlas_labels_inside_brain_fraction
        == 1.0
    )

    with Image.open(
        result.patient_image_path
    ) as image:
        assert (
            image.width
            == 128 * 3
        )

        assert (
            image.height
            == 82
            + 128 * 3
        )

    with Image.open(
        result.atlas_image_path
    ) as image:
        assert (
            image.width
            == 128 * 3
        )

        assert (
            image.height
            == 82
            + 128 * 3
        )