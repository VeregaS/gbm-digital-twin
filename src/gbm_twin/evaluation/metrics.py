from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import (
    binary_erosion,
    distance_transform_edt,
)

from gbm_twin.data.nifti import NiftiVolume

BoolArray = NDArray[np.bool_]


def _as_bool_mask(
    value: np.ndarray,
) -> BoolArray:
    return np.asarray(
        value,
        dtype=np.bool_,
    )


def _validate_mask_pair(
    first: np.ndarray,
    second: np.ndarray,
) -> tuple[
    BoolArray,
    BoolArray,
]:
    first_mask = _as_bool_mask(
        first
    )

    second_mask = _as_bool_mask(
        second
    )

    if (
        first_mask.shape
        != second_mask.shape
    ):
        raise ValueError(
            "Shape mismatch: "
            f"{first_mask.shape} "
            f"vs {second_mask.shape}"
        )

    if first_mask.ndim != 3:
        raise ValueError(
            "Spatial metrics require "
            "3D masks"
        )

    return (
        first_mask,
        second_mask,
    )


def _validate_spacing(
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> None:
    if len(spacing) != 3:
        raise ValueError(
            "Spacing must contain "
            "exactly three values"
        )

    if any(
        not math.isfinite(value)
        or value <= 0.0
        for value in spacing
    ):
        raise ValueError(
            "Spacing values must be "
            "finite and positive"
        )


def _surface(
    mask: BoolArray,
) -> BoolArray:
    eroded = np.asarray(
        binary_erosion(
            mask,
            border_value=0,
        ),
        dtype=np.bool_,
    )

    return np.asarray(
        mask & ~eroded,
        dtype=np.bool_,
    )


def mask_volume_cm3(
    volume: NiftiVolume,
    *,
    threshold: float = 0.5,
) -> float:
    mask = (
        volume.data
        > threshold
    )

    voxel_count = int(
        np.count_nonzero(
            mask
        )
    )

    voxel_volume_mm3 = float(
        np.prod(
            volume.spacing
        )
    )

    volume_mm3 = (
        voxel_count
        * voxel_volume_mm3
    )

    return (
        volume_mm3
        / 1000.0
    )


def dice_score(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    (
        first_mask,
        second_mask,
    ) = _validate_mask_pair(
        first,
        second,
    )

    intersection = int(
        np.count_nonzero(
            first_mask
            & second_mask
        )
    )

    total = (
        int(
            np.count_nonzero(
                first_mask
            )
        )
        + int(
            np.count_nonzero(
                second_mask
            )
        )
    )

    if total == 0:
        return 1.0

    return (
        2.0
        * intersection
        / total
    )


def relative_volume_error(
    predicted: np.ndarray,
    observed: np.ndarray,
) -> float:
    (
        predicted_mask,
        observed_mask,
    ) = _validate_mask_pair(
        predicted,
        observed,
    )

    observed_count = int(
        np.count_nonzero(
            observed_mask
        )
    )

    if observed_count == 0:
        raise ValueError(
            "Observed mask is empty"
        )

    predicted_count = int(
        np.count_nonzero(
            predicted_mask
        )
    )

    return (
        abs(
            predicted_count
            - observed_count
        )
        / observed_count
    )


def centroid_distance_mm(
    first: np.ndarray,
    second: np.ndarray,
    *,
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> float | None:
    _validate_spacing(
        spacing
    )

    (
        first_mask,
        second_mask,
    ) = _validate_mask_pair(
        first,
        second,
    )

    if (
        not np.any(first_mask)
        or not np.any(second_mask)
    ):
        return None

    spacing_array = np.asarray(
        spacing,
        dtype=np.float64,
    )

    first_coordinates = np.asarray(
        np.argwhere(
            first_mask
        ),
        dtype=np.float64,
    )

    second_coordinates = np.asarray(
        np.argwhere(
            second_mask
        ),
        dtype=np.float64,
    )

    first_centroid_mm = (
        first_coordinates
        * spacing_array
    ).mean(
        axis=0
    )

    second_centroid_mm = (
        second_coordinates
        * spacing_array
    ).mean(
        axis=0
    )

    return float(
        np.linalg.norm(
            first_centroid_mm
            - second_centroid_mm
        )
    )


def hausdorff95_mm(
    first: np.ndarray,
    second: np.ndarray,
    *,
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> float | None:
    _validate_spacing(
        spacing
    )

    (
        first_mask,
        second_mask,
    ) = _validate_mask_pair(
        first,
        second,
    )

    if (
        not np.any(first_mask)
        or not np.any(second_mask)
    ):
        return None

    first_surface = _surface(
        first_mask
    )

    second_surface = _surface(
        second_mask
    )

    distance_to_second = np.asarray(
        distance_transform_edt(
            ~second_surface,
            sampling=spacing,
        ),
        dtype=np.float64,
    )

    distance_to_first = np.asarray(
        distance_transform_edt(
            ~first_surface,
            sampling=spacing,
        ),
        dtype=np.float64,
    )

    first_to_second = (
        distance_to_second[
            first_surface
        ]
    )

    second_to_first = (
        distance_to_first[
            second_surface
        ]
    )

    distances = np.concatenate(
        (
            first_to_second,
            second_to_first,
        )
    )

    return float(
        np.percentile(
            distances,
            95.0,
        )
    )