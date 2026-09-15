from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import gbm_twin.workflows.viewer as viewer_module
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.viewer import (
    clear_viewer_cache,
    get_viewer_volume_metadata,
    render_viewer_slice_png,
)


def make_volume(
    name: str,
    data: np.ndarray,
) -> NiftiVolume:
    return NiftiVolume(
        path=Path(name),
        data=data,
        affine=np.eye(
            4,
            dtype=np.float64,
        ),
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )


def make_prepared(
) -> PreparedPatientTimepoint:
    image = np.arange(
        4 * 5 * 6,
        dtype=np.float32,
    ).reshape(
        (4, 5, 6)
    )

    gtv = np.zeros(
        image.shape,
        dtype=np.float32,
    )

    gtv[
        1:3,
        2:4,
        2:4,
    ] = 1.0

    brain = np.ones(
        image.shape,
        dtype=np.float32,
    )

    return PreparedPatientTimepoint(
        patient_id=108,
        name="t1",
        days_from_baseline=98.0,
        t1gd=make_volume(
            "t1gd.nii.gz",
            image,
        ),
        gtv=make_volume(
            "gtv.nii.gz",
            gtv,
        ),
        brain_mask=make_volume(
            "brain.nii.gz",
            brain,
        ),
    )


@pytest.fixture(autouse=True)
def reset_cache():
    clear_viewer_cache()

    yield

    clear_viewer_cache()


def test_get_viewer_volume_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = make_prepared()

    monkeypatch.setattr(
        viewer_module,
        "prepare_patient_timepoint",
        lambda **kwargs: prepared,
    )

    result = (
        get_viewer_volume_metadata(
            metadata_root=(
                tmp_path / "metadata"
            ),
            patients_root=(
                tmp_path / "patients"
            ),
            patient_id=108,
            timepoint_name="t1",
        )
    )

    assert result.patient_id == 108
    assert result.timepoint_name == "t1"

    assert result.shape == (
        4,
        5,
        6,
    )

    assert result.spacing == (
        2.0,
        2.0,
        2.0,
    )

    planes = {
        plane.name: plane
        for plane in result.planes
    }

    assert (
        planes["axial"].size
        == 6
    )

    assert (
        planes["coronal"].size
        == 5
    )

    assert (
        planes["sagittal"].size
        == 4
    )

    assert result.gtv_voxels == 8

    assert result.gtv_volume_cm3 == (
        pytest.approx(
            0.064
        )
    )


def test_render_viewer_slice_png(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = make_prepared()

    monkeypatch.setattr(
        viewer_module,
        "prepare_patient_timepoint",
        lambda **kwargs: prepared,
    )

    png = render_viewer_slice_png(
        metadata_root=(
            tmp_path / "metadata"
        ),
        patients_root=(
            tmp_path / "patients"
        ),
        patient_id=108,
        timepoint_name="t1",
        plane="axial",
        index=3,
        overlay_gtv=True,
    )

    assert png.startswith(
        b"\x89PNG\r\n\x1a\n"
    )

    output = tmp_path / "slice.png"

    output.write_bytes(
        png
    )

    with Image.open(
        output
    ) as image:
        assert image.size == (
            4,
            5,
        )

        assert image.mode == "RGB"


def test_render_viewer_slice_rejects_bad_index(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = make_prepared()

    monkeypatch.setattr(
        viewer_module,
        "prepare_patient_timepoint",
        lambda **kwargs: prepared,
    )

    with pytest.raises(
        IndexError,
        match="outside",
    ):
        render_viewer_slice_png(
            metadata_root=(
                tmp_path / "metadata"
            ),
            patients_root=(
                tmp_path / "patients"
            ),
            patient_id=108,
            timepoint_name="t1",
            plane="axial",
            index=999,
        )