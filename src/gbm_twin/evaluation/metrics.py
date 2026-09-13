import numpy as np

from gbm_twin.data.nifti import NiftiVolume


def mask_volume_cm3(
    volume: NiftiVolume,
    *,
    threshold: float = 0.5,
) -> float:
    mask = volume.data > threshold

    voxel_count = int(np.count_nonzero(mask))

    voxel_volume_mm3 = float(np.prod(volume.spacing))

    volume_mm3 = voxel_count * voxel_volume_mm3

    return volume_mm3 / 1000.0