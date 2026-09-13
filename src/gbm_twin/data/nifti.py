from dataclasses import dataclass
from pathlib import Path

import nibabel as nib
import numpy as np


@dataclass(frozen=True)
class NiftiVolume:
    path: Path
    data: np.ndarray
    affine: np.ndarray
    spacing: tuple[float, float, float]

    @property
    def shape(self) -> tuple[int, ...]:
        return self.data.shape


def load_nifti(path: Path) -> NiftiVolume:
    if not path.exists():
        raise FileNotFoundError(path)

    image = nib.load(path)

    if not isinstance(image, nib.Nifti1Image):
        raise TypeError(
            f"Expected NIfTI-1 image, got {type(image).__name__}: {path}"
        )

    data = np.asarray(image.dataobj)

    if data.ndim != 3:
        raise ValueError(
            f"Expected 3D NIfTI volume, got shape {data.shape}: {path}"
        )

    zooms = np.asarray(image.header.get_zooms(), dtype=float)

    if len(zooms) < 3:
        raise ValueError(
            f"Expected at least 3 spatial dimensions, got {len(zooms)}: {path}"
        )

    spacing = (
        float(zooms[0]),
        float(zooms[1]),
        float(zooms[2]),
    )

    affine = image.affine

    if affine is None:
        raise ValueError(f"NIfTI image has no affine: {path}")

    return NiftiVolume(
        path=path,
        data=data,
        affine=np.asarray(affine),
        spacing=spacing,
    )
    
def same_geometry(
    first: NiftiVolume,
    second: NiftiVolume,
    *,
    atol: float = 1e-5,
) -> bool:
    return (
        first.shape == second.shape
        and np.allclose(first.spacing, second.spacing, atol=atol)
        and np.allclose(first.affine, second.affine, atol=atol)
    )