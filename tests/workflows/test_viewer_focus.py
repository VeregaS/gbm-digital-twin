from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.viewer_focus as focus_module
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.viewer_focus import (
    clear_viewer_focus_cache,
    get_viewer_focus_metadata,
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
    *,
    empty_gtv: bool = False,
) -> PreparedPatientTimepoint:
    shape = (
        6,
        7,
        8,
    )

    image = np.ones(
        shape,
        dtype=np.float32,
    )

    gtv = np.zeros(
        shape,
        dtype=np.float32,
    )

    if not empty_gtv:
        gtv[
            1:5,
            2:6,
            4:7,
        ] = 1.0

    brain = np.ones(
        shape,
        dtype=np.float32,
    )

    return PreparedPatientTimepoint(
        patient_id=214,
        name="t1",
        days_from_baseline=182.0,
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
    clear_viewer_focus_cache()

    yield

    clear_viewer_focus_cache()


def test_focus_uses_middle_peak_gtv_slice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = make_prepared()

    monkeypatch.setattr(
        focus_module,
        "prepare_patient_timepoint",
        lambda **kwargs: prepared,
    )

    result = get_viewer_focus_metadata(
        metadata_root=(
            tmp_path / "metadata"
        ),
        patients_root=(
            tmp_path / "patients"
        ),
        patient_id=214,
        timepoint_name="t1",
    )

    assert result.patient_id == 214
    assert result.timepoint_name == "t1"

    assert result.axial_index == 5
    assert result.coronal_index == 4
    assert result.sagittal_index == 3

    assert result.gtv_voxels == 48


def test_focus_is_none_for_empty_gtv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared = make_prepared(
        empty_gtv=True
    )

    monkeypatch.setattr(
        focus_module,
        "prepare_patient_timepoint",
        lambda **kwargs: prepared,
    )

    result = get_viewer_focus_metadata(
        metadata_root=(
            tmp_path / "metadata"
        ),
        patients_root=(
            tmp_path / "patients"
        ),
        patient_id=214,
        timepoint_name="t1",
    )

    assert result.axial_index is None
    assert result.coronal_index is None
    assert result.sagittal_index is None
    assert result.gtv_voxels == 0
