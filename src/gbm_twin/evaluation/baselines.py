import math

import numpy as np
from scipy.ndimage import distance_transform_edt


def extrapolate_volume(
    volume_t0: float,
    volume_t1: float,
    *,
    dt01_days: float,
    dt12_days: float,
) -> float:
    if volume_t0 <= 0 or volume_t1 <= 0:
        raise ValueError("Volumes must be positive")

    if dt01_days <= 0 or dt12_days <= 0:
        raise ValueError("Time intervals must be positive")

    growth_rate = math.log(volume_t1 / volume_t0) / dt01_days

    return volume_t1 * math.exp(
        growth_rate * dt12_days
    )
    
def expand_mask_to_volume(
    mask: np.ndarray,
    *,
    target_volume_cm3: float,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    mask = mask.astype(bool)

    voxel_volume_cm3 = float(np.prod(spacing)) / 1000.0

    target_voxels = round(
        target_volume_cm3 / voxel_volume_cm3
    )

    current_voxels = int(np.count_nonzero(mask))

    if target_voxels < current_voxels:
        raise ValueError(
            "Target volume is smaller than current mask volume"
        )

    if target_voxels == current_voxels:
        return mask.copy()

    distances = np.asarray(
        distance_transform_edt(
            ~mask,
            sampling=spacing,
        ),
        dtype=float,
    )

    outside_indices = np.flatnonzero(~mask)

    flat_distances = distances.ravel()

    order = np.argsort(
        flat_distances[outside_indices]
    )

    voxels_to_add = target_voxels - current_voxels

    selected = outside_indices[
        order[:voxels_to_add]
    ]

    result = mask.copy()
    result.flat[selected] = True

    return result