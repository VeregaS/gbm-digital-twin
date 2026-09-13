from pathlib import Path

import numpy as np

from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.preprocessing.resampling import resample_volume


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