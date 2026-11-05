from pathlib import Path

import numpy as np

from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.preprocessing.resampling import (
    resample_volume,
    resample_volume_to_reference,
)


def test_resample_mask_to_target_spacing() -> None:
    data = np.zeros((32, 32, 32), dtype=np.uint8)
    data[8:24, 8:24, 8:24] = 1

    volume = NiftiVolume(
        path=Path("mask.nii.gz"),
        data=data,
        affine=np.eye(4),
        spacing=(1.0, 1.0, 1.0),
    )

    result = resample_volume(
        volume,
        target_spacing=(2.0, 2.0, 2.0),
        is_mask=True,
    )

    assert np.allclose(result.spacing, (2.0, 2.0, 2.0))
    assert set(np.unique(result.data)).issubset({0, 1})
    assert result.shape[0] < volume.shape[0]


def test_resample_volume_to_reference_matches_exact_geometry() -> None:
    source = NiftiVolume(
        path=Path("dose.nii.gz"),
        data=np.ones((8, 8, 8), dtype=np.float32),
        affine=np.diag([2.0, 2.0, 2.0, 1.0]),
        spacing=(2.0, 2.0, 2.0),
    )
    reference_affine = np.asarray(
        [
            [1.0, 0.0, 0.0, -2.0],
            [0.0, 1.0, 0.0, -2.0],
            [0.0, 0.0, 1.0, -2.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    reference = NiftiVolume(
        path=Path("t1gd.nii.gz"),
        data=np.zeros((16, 16, 16), dtype=np.float32),
        affine=reference_affine,
        spacing=(1.0, 1.0, 1.0),
    )

    result = resample_volume_to_reference(source, reference)

    assert result.shape == reference.shape
    assert np.allclose(result.affine, reference.affine)
    assert np.allclose(result.spacing, reference.spacing)
