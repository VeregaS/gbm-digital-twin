from pathlib import Path

import nibabel as nib
import numpy as np
from nibabel.processing import resample_from_to, resample_to_output

from gbm_twin.data.nifti import NiftiVolume


def _volume_from_image(
    *,
    source_path: Path,
    image: nib.Nifti1Image,
    is_mask: bool,
) -> NiftiVolume:
    data = np.asarray(image.dataobj)

    if is_mask:
        data = (data > 0.5).astype(np.uint8)

    zooms = np.asarray(image.header.get_zooms(), dtype=float)
    spacing = (
        float(zooms[0]),
        float(zooms[1]),
        float(zooms[2]),
    )

    affine = image.affine

    if affine is None:
        raise ValueError("Resampled image has no affine")

    return NiftiVolume(
        path=Path(source_path),
        data=data,
        affine=np.asarray(affine),
        spacing=spacing,
    )


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

    if not isinstance(resampled, nib.Nifti1Image):
        resampled = nib.Nifti1Image(
            np.asarray(resampled.dataobj),
            resampled.affine,
            resampled.header,
        )

    return _volume_from_image(
        source_path=volume.path,
        image=resampled,
        is_mask=is_mask,
    )


def resample_volume_to_reference(
    volume: NiftiVolume,
    reference: NiftiVolume,
    *,
    is_mask: bool = False,
) -> NiftiVolume:
    """Resample a volume directly onto an existing reference voxel grid.

    Stage 8 uses this for FLAIR/DWI/RTDOSE so all model inputs share the exact
    MRI grid, not merely the same nominal voxel spacing.
    """

    if len(reference.shape) != 3:
        raise ValueError("Reference volume must be 3D")

    source = nib.Nifti1Image(
        volume.data.astype(np.float32),
        volume.affine,
    )

    target = (
        tuple(int(value) for value in reference.shape),
        np.asarray(reference.affine, dtype=float),
    )

    resampled = resample_from_to(
        source,
        target,
        order=0 if is_mask else 1,
    )

    if not isinstance(resampled, nib.Nifti1Image):
        resampled = nib.Nifti1Image(
            np.asarray(resampled.dataobj),
            resampled.affine,
            resampled.header,
        )

    return _volume_from_image(
        source_path=volume.path,
        image=resampled,
        is_mask=is_mask,
    )
