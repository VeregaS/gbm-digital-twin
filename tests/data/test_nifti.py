from pathlib import Path

import nibabel as nib
import numpy as np

from gbm_twin.data.nifti import load_nifti, same_geometry


def create_nifti(path: Path, shape: tuple[int, int, int]) -> None:
    data = np.zeros(shape, dtype=np.float32)
    affine = np.eye(4)

    nib.save(
        nib.Nifti1Image(data, affine),
        path,
    )


def test_load_nifti(tmp_path: Path) -> None:
    path = tmp_path / "image.nii.gz"

    create_nifti(path, (16, 20, 24))

    volume = load_nifti(path)

    assert volume.shape == (16, 20, 24)
    assert volume.spacing == (1.0, 1.0, 1.0)


def test_same_geometry(tmp_path: Path) -> None:
    first_path = tmp_path / "first.nii.gz"
    second_path = tmp_path / "second.nii.gz"

    create_nifti(first_path, (16, 20, 24))
    create_nifti(second_path, (16, 20, 24))

    first = load_nifti(first_path)
    second = load_nifti(second_path)

    assert same_geometry(first, second)