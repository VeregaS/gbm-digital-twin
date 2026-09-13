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

    growth_rate = math.log(
        volume_t1 / volume_t0
    ) / dt01_days

    return volume_t1 * math.exp(
        growth_rate * dt12_days
    )


def resize_mask_to_volume(
    mask: np.ndarray,
    *,
    target_volume_cm3: float,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError("Mask must be 3D")

    if target_volume_cm3 <= 0:
        raise ValueError(
            "Target volume must be positive"
        )

    if any(value <= 0 for value in spacing):
        raise ValueError(
            "Spacing values must be positive"
        )

    mask = mask.astype(bool)

    current_voxels = int(
        np.count_nonzero(mask)
    )

    if current_voxels == 0:
        raise ValueError(
            "Mask must contain at least one voxel"
        )

    voxel_volume_cm3 = (
        float(np.prod(spacing)) / 1000.0
    )

    target_voxels = max(
        1,
        round(
            target_volume_cm3
            / voxel_volume_cm3
        ),
    )

    if target_voxels > mask.size:
        raise ValueError(
            "Target volume exceeds "
            "computational grid volume"
        )

    if target_voxels == current_voxels:
        return mask.copy()

    if target_voxels > current_voxels:
        return _expand_mask(
            mask,
            target_voxels=target_voxels,
            spacing=spacing,
        )

    return _shrink_mask(
        mask,
        target_voxels=target_voxels,
        spacing=spacing,
    )


def _expand_mask(
    mask: np.ndarray,
    *,
    target_voxels: int,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    distances = np.asarray(
        distance_transform_edt(
            ~mask,
            sampling=spacing,
        ),
        dtype=float,
    )

    outside_indices = np.flatnonzero(
        ~mask
    )

    flat_distances = distances.ravel()

    order = np.argsort(
        flat_distances[outside_indices],
        kind="stable",
    )

    voxels_to_add = (
        target_voxels
        - int(np.count_nonzero(mask))
    )

    selected = outside_indices[
        order[:voxels_to_add]
    ]

    result = mask.copy()
    result.flat[selected] = True

    return result


def _shrink_mask(
    mask: np.ndarray,
    *,
    target_voxels: int,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    distances = np.asarray(
        distance_transform_edt(
            mask,
            sampling=spacing,
        ),
        dtype=float,
    )

    inside_indices = np.flatnonzero(
        mask
    )

    flat_distances = distances.ravel()

    order = np.argsort(
        -flat_distances[inside_indices],
        kind="stable",
    )

    selected = inside_indices[
        order[:target_voxels]
    ]

    result = np.zeros_like(
        mask,
        dtype=bool,
    )

    result.flat[selected] = True

    return result