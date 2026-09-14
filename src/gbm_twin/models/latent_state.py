from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt


@dataclass(frozen=True)
class LatentStateParameters:
    transition_width_mm: float = 4.0

    def __post_init__(self) -> None:
        if self.transition_width_mm <= 0:
            raise ValueError(
                "transition_width_mm must be positive"
            )


def signed_distance_from_mask(
    mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    binary = np.asarray(
        mask,
        dtype=bool,
    )

    if binary.ndim != 3:
        raise ValueError(
            "mask must be 3-dimensional"
        )

    if not np.any(binary):
        raise ValueError(
            "mask must contain at least one active voxel"
        )

    if any(
        value <= 0
        for value in spacing
    ):
        raise ValueError(
            "spacing values must be positive"
        )

    inside_distance = np.asarray(
        distance_transform_edt(
            binary,
            sampling=spacing,
            return_distances=True,
            return_indices=False,
        ),
        dtype=np.float64,
    )

    outside_distance = np.asarray(
        distance_transform_edt(
            ~binary,
            sampling=spacing,
            return_distances=True,
            return_indices=False,
        ),
        dtype=np.float64,
    )

    return (
        inside_distance
        - outside_distance
    )


def latent_state_from_gtv(
    gtv: np.ndarray,
    brain_mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    parameters: LatentStateParameters | None = None,
) -> np.ndarray:
    params = (
        parameters
        if parameters is not None
        else LatentStateParameters()
    )

    tumor = np.asarray(
        gtv,
        dtype=bool,
    )

    brain = np.asarray(
        brain_mask,
        dtype=bool,
    )

    if tumor.shape != brain.shape:
        raise ValueError(
            "gtv and brain_mask must have the same shape"
        )

    if np.any(
        tumor & ~brain
    ):
        brain = (
            brain
            | tumor
        )

    signed_distance = signed_distance_from_mask(
        tumor,
        spacing=spacing,
    )

    scaled = (
        signed_distance
        / params.transition_width_mm
    )

    scaled = np.clip(
        scaled,
        -60.0,
        60.0,
    )

    field = (
        1.0
        / (
            1.0
            + np.exp(-scaled)
        )
    )

    field = np.where(
        brain,
        field,
        0.0,
    )

    return field.astype(
        np.float32,
        copy=False,
    )