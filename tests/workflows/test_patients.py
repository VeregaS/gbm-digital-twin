from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import gbm_twin.workflows.patients as patients_module
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.workflows.patients import (
    prepare_patient_timepoint,
)


def make_volume(
    name: str,
) -> NiftiVolume:
    return NiftiVolume(
        path=Path(name),
        data=np.zeros(
            (4, 5, 6),
            dtype=np.float32,
        ),
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


def test_prepare_patient_timepoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timepoint = SimpleNamespace(
        name="t0",
        days_from_baseline=0,
    )

    patient = SimpleNamespace(
        get_timepoint=(
            lambda name: timepoint
        ),
    )

    class FakeMetadata:
        def __init__(
            self,
            metadata_root: Path,
        ) -> None:
            self.metadata_root = (
                metadata_root
            )

        def patient(
            self,
            patient_id: int,
        ):
            assert patient_id == 42
            return patient

    study = SimpleNamespace(
        t1gd=make_volume(
            "t1gd.nii.gz"
        ),
        gtv=make_volume(
            "gtv.nii.gz"
        ),
        brain_mask=make_volume(
            "brain.nii.gz"
        ),
    )

    monkeypatch.setattr(
        patients_module,
        "CFBMetadata",
        FakeMetadata,
    )

    monkeypatch.setattr(
        patients_module,
        "load_patient_timepoint",
        lambda *args, **kwargs: study,
    )

    monkeypatch.setattr(
        patients_module,
        "resample_volume",
        lambda volume, spacing, is_mask: (
            volume
        ),
    )

    result = (
        prepare_patient_timepoint(
            metadata_root=Path(
                "metadata"
            ),
            patients_root=Path(
                "patients"
            ),
            patient_id=42,
            timepoint_name="t0",
        )
    )

    assert result.patient_id == 42
    assert result.name == "t0"

    assert (
        result.days_from_baseline
        == 0.0
    )

    assert result.spacing == (
        2.0,
        2.0,
        2.0,
    )


def test_prepare_patient_timepoint_rejects_bad_spacing(
) -> None:
    with pytest.raises(
        ValueError,
        match="positive",
    ):
        prepare_patient_timepoint(
            metadata_root=Path(
                "metadata"
            ),
            patients_root=Path(
                "patients"
            ),
            patient_id=42,
            timepoint_name="t0",
            target_spacing=(
                2.0,
                0.0,
                2.0,
            ),
        )


def test_prepare_patient_timepoint_rejects_geometry_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timepoint = SimpleNamespace(
        name="t0",
        days_from_baseline=0,
    )

    patient = SimpleNamespace(
        get_timepoint=(
            lambda name: timepoint
        ),
    )

    class FakeMetadata:
        def __init__(
            self,
            metadata_root: Path,
        ) -> None:
            self.metadata_root = (
                metadata_root
            )

        def patient(
            self,
            patient_id: int,
        ):
            return patient

    t1gd = make_volume(
        "t1gd.nii.gz"
    )

    gtv = make_volume(
        "gtv.nii.gz"
    )

    brain = NiftiVolume(
        path=Path(
            "brain.nii.gz"
        ),
        data=np.zeros(
            (5, 5, 6),
            dtype=np.float32,
        ),
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

    study = SimpleNamespace(
        t1gd=t1gd,
        gtv=gtv,
        brain_mask=brain,
    )

    monkeypatch.setattr(
        patients_module,
        "CFBMetadata",
        FakeMetadata,
    )

    monkeypatch.setattr(
        patients_module,
        "load_patient_timepoint",
        lambda *args, **kwargs: study,
    )

    monkeypatch.setattr(
        patients_module,
        "resample_volume",
        lambda volume, spacing, is_mask: (
            volume
        ),
    )

    with pytest.raises(
        ValueError,
        match="GTV/brain geometry mismatch",
    ):
        prepare_patient_timepoint(
            metadata_root=Path(
                "metadata"
            ),
            patients_root=Path(
                "patients"
            ),
            patient_id=42,
            timepoint_name="t0",
        )