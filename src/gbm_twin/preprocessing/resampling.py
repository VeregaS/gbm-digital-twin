from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.processing import resample_to_output

from gbm_twin.data.nifti import NiftiVolume


def resample_volume(
    volume: NiftiVolume,
    target_spacing: tuple[float, float, float],
    *,
    is_mask: bool = False,
) -> NiftiVolume:
    if any(value <= 0 for value in target_spacing):
        raise ValueError("Target spacing must be positive")

    image = nib.Nifti1Image(
        volume.data.astype(np.float32),
        volume.affine,
    )

    resampled = resample_to_output(
        image,
        voxel_sizes=target_spacing,
        order=0 if is_mask else 1,
    )

    data = np.asarray(resampled.dataobj)

    if is_mask:
        data = (data > 0.5).astype(np.uint8)

    zooms = np.asarray(resampled.header.get_zooms(), dtype=float)

    spacing = (
        float(zooms[0]),
        float(zooms[1]),
        float(zooms[2]),
    )

    affine = resampled.affine

    if affine is None:
        raise ValueError("Resampled image has no affine")

    return NiftiVolume(
        path=Path(volume.path),
        data=data,
        affine=np.asarray(affine),
        spacing=spacing,
    )