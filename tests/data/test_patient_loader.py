from pathlib import Path

import nibabel as nib
import numpy as np

from gbm_twin.data.models import Timepoint
from gbm_twin.data.patient_loader import load_patient_timepoint


def create_nifti(path: Path, shape: tuple[int, int, int]) -> None:
    data = np.zeros(shape, dtype=np.float32)
    affine = np.eye(4)
    nib.save(nib.Nifti1Image(data, affine), path)


def test_load_patient_timepoint(tmp_path: Path) -> None:
    patients_root = tmp_path
    patient_dir = patients_root / "42" / "t0"
    patient_dir.mkdir(parents=True)

    create_nifti(patient_dir / "42_t0_t1gd.nii.gz", (16, 16, 8))
    create_nifti(patient_dir / "42_t0_gtv.nii.gz", (16, 16, 8))
    create_nifti(patient_dir / "42_t0_brain_mask.nii.gz", (16, 16, 8))

    study = load_patient_timepoint(
        patients_root=patients_root,
        patient_id=42,
        timepoint=Timepoint(name="t0", days_from_baseline=0),
    )

    assert study.patient_id == "42"
    assert study.timepoint.name == "t0"
    assert study.t1gd.shape == (16, 16, 8)
    assert study.gtv.shape == (16, 16, 8)
    assert study.brain_mask.shape == (16, 16, 8)