from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt


@dataclass(frozen=True)
class MRIDetectionObservationParameters:
    enhancing_threshold: float = 0.80
    infiltrative_threshold: float = 0.16
    transition_width_mm: float = 4.0

    def __post_init__(self) -> None:
        if not 0.0 < self.infiltrative_threshold < 1.0:
            raise ValueError("infiltrative_threshold must be within (0, 1)")

        if not 0.0 < self.enhancing_threshold < 1.0:
            raise ValueError("enhancing_threshold must be within (0, 1)")

        if self.infiltrative_threshold >= self.enhancing_threshold:
            raise ValueError(
                "infiltrative_threshold must be lower than enhancing_threshold"
            )

        if self.transition_width_mm <= 0.0:
            raise ValueError("transition_width_mm must be positive")


def _validate_spacing(spacing: tuple[float, float, float]) -> None:
    if len(spacing) != 3 or any(value <= 0.0 for value in spacing):
        raise ValueError("spacing must contain three positive values")


def _signed_distance(
    mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    binary = np.asarray(mask, dtype=bool)

    if binary.ndim != 3:
        raise ValueError("detection mask must be 3D")

    if not np.any(binary):
        raise ValueError("detection mask must contain active voxels")

    inside = distance_transform_edt(
        binary,
        sampling=spacing,
    )
    outside = distance_transform_edt(
        ~binary,
        sampling=spacing,
    )

    return np.asarray(inside - outside, dtype=np.float64)


def _logit(probability: float) -> float:
    return math.log(probability / (1.0 - probability))


def _profile_from_detection_mask(
    mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    boundary_density: float,
    transition_width_mm: float,
) -> np.ndarray:
    distance = _signed_distance(mask, spacing=spacing)
    scaled = (
        distance / transition_width_mm
        + _logit(boundary_density)
    )
    scaled = np.clip(scaled, -60.0, 60.0)

    return 1.0 / (1.0 + np.exp(-scaled))


def latent_density_from_mri_detection(
    enhancing_mask: np.ndarray,
    brain_mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    infiltrative_mask: np.ndarray | None = None,
    parameters: MRIDetectionObservationParameters | None = None,
) -> np.ndarray:
    """Construct a latent tumor-density field from MRI detection regions.

    The MRI masks are treated as observation surfaces, not direct cell-density
    measurements. The enhancing boundary is associated with a high-density
    detection threshold and an optional infiltrative/FLAIR boundary with a
    lower-density threshold. This is a model assumption and must remain
    versioned in experiment provenance.
    """

    _validate_spacing(spacing)
    params = parameters or MRIDetectionObservationParameters()

    enhancing = np.asarray(enhancing_mask, dtype=bool)
    brain = np.asarray(brain_mask, dtype=bool)

    if enhancing.shape != brain.shape:
        raise ValueError("enhancing_mask and brain_mask must match")

    if enhancing.ndim != 3:
        raise ValueError("MRI detection masks must be 3D")

    if not np.any(enhancing):
        raise ValueError("enhancing_mask must contain active voxels")

    # A tumor annotation outside a derived brain mask should not disappear
    # from the biological state. Preserve it in the computational domain and
    # let QC report the geometry problem separately.
    effective_brain = brain | enhancing

    enhancing_profile = _profile_from_detection_mask(
        enhancing,
        spacing=spacing,
        boundary_density=params.enhancing_threshold,
        transition_width_mm=params.transition_width_mm,
    )

    field = enhancing_profile

    if infiltrative_mask is not None:
        infiltrative = np.asarray(infiltrative_mask, dtype=bool)

        if infiltrative.shape != enhancing.shape:
            raise ValueError(
                "infiltrative_mask and enhancing_mask must match"
            )

        if not np.any(infiltrative):
            raise ValueError("infiltrative_mask must contain active voxels")

        if np.any(enhancing & ~infiltrative):
            raise ValueError(
                "enhancing region must be contained in infiltrative region"
            )

        effective_brain = effective_brain | infiltrative

        infiltrative_profile = _profile_from_detection_mask(
            infiltrative,
            spacing=spacing,
            boundary_density=params.infiltrative_threshold,
            transition_width_mm=params.transition_width_mm,
        )

        field = np.maximum(
            enhancing_profile,
            infiltrative_profile,
        )

    field = np.where(effective_brain, field, 0.0)
    np.clip(field, 0.0, 1.0, out=field)

    return field.astype(np.float32, copy=False)
