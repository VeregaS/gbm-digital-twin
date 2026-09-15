from pathlib import Path

import numpy as np
from PIL import Image

from gbm_twin.anatomy.qc import (
    render_registration_qc_png,
)


def test_render_registration_qc_png(
    tmp_path: Path,
) -> None:
    shape = (
        40,
        42,
        36,
    )

    patient_t1 = np.zeros(
        shape,
        dtype=np.float32,
    )

    patient_brain = np.zeros(
        shape,
        dtype=bool,
    )

    atlas_brain = np.zeros(
        shape,
        dtype=bool,
    )

    labels = np.zeros(
        shape,
        dtype=np.int16,
    )

    patient_brain[
        6:34,
        7:35,
        5:31,
    ] = True

    atlas_brain[
        7:35,
        7:35,
        5:31,
    ] = True

    labels[
        15:24,
        15:25,
        12:22,
    ] = 4

    x = np.linspace(
        0.0,
        1.0,
        shape[0],
        dtype=np.float32,
    )

    y = np.linspace(
        0.0,
        1.0,
        shape[1],
        dtype=np.float32,
    )

    z = np.linspace(
        0.0,
        1.0,
        shape[2],
        dtype=np.float32,
    )

    patient_t1[:] = (
        x[:, None, None]
        + y[None, :, None]
        + z[None, None, :]
    )

    patient_t1[
        ~patient_brain
    ] = 0.0

    output_path = (
        tmp_path
        / "registration_qc.png"
    )

    result = (
        render_registration_qc_png(
            patient_t1=(
                patient_t1
            ),
            patient_brain_mask=(
                patient_brain
            ),
            registered_atlas_brain_mask=(
                atlas_brain
            ),
            registered_labels=(
                labels
            ),
            output_path=(
                output_path
            ),
            patient_id=108,
            timepoint_name="t1",
            tile_size=128,
        )
    )

    assert (
        result.output_path
        == output_path.resolve()
    )

    assert (
        output_path.is_file()
    )

    assert (
        result.brain_dice
        > 0.9
    )

    assert (
        result
        .labeled_inside_brain_fraction
        == 1.0
    )

    with Image.open(
        output_path
    ) as image:
        assert image.mode == "RGB"

        assert image.width == (
            128 * 3
        )

        assert image.height == (
            94
            + 128 * 3
        )