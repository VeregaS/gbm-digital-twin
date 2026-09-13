from pathlib import Path

import numpy as np

from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.evaluation.metrics import mask_volume_cm3


def test_mask_volume_cm3() -> None:
    data = np.zeros((10, 10, 10), dtype=np.uint8)
    data[:5, :5, :4] = 1

    volume = NiftiVolume(
        path=Path("test.nii.gz"),
        data=data,
        affine=np.eye(4),
        spacing=(1.0, 1.0, 1.0),
    )

    assert mask_volume_cm3(volume) == 0.1