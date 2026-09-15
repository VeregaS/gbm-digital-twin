from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy.ndimage import (
    binary_fill_holes,
    generate_binary_structure,
)
from scipy.ndimage import (
    label as connected_components,
)


@dataclass(frozen=True)
class RegistrationMaskReport:
    original_voxels: int

    cleaned_voxels: int

    component_count: int

    removed_voxels: int

    retained_fraction: float


@dataclass(frozen=True)
class RegistrationMaskResult:
    mask: np.ndarray

    report: RegistrationMaskReport


def clean_registration_mask(
    mask: np.ndarray,
) -> RegistrationMaskResult:
    binary = np.asarray(
        mask,
        dtype=bool,
    )

    if binary.ndim != 3:
        raise ValueError(
            "Registration mask must "
            f"be 3D, got {binary.shape}"
        )

    original_voxels = int(
        np.count_nonzero(
            binary
        )
    )

    if original_voxels == 0:
        raise ValueError(
            "Registration mask is empty"
        )

    structure = (
        generate_binary_structure(
            rank=3,
            connectivity=3,
        )
    )

    component_labels = np.zeros(
        binary.shape,
        dtype=np.int32,
    )

    component_count = cast(
        int,
        connected_components(
            binary,
            structure=structure,
            output=component_labels,
        ),
    )

    if component_count <= 0:
        raise RuntimeError(
            "Connected-component "
            "analysis found no "
            "foreground components"
        )

    component_sizes = np.bincount(
        component_labels.ravel(),
        minlength=(
            component_count + 1
        ),
    )

    if component_sizes.size <= 1:
        raise RuntimeError(
            "Connected-component "
            "analysis produced no "
            "foreground components"
        )

    component_sizes[0] = 0

    largest_component_label = int(
        np.argmax(
            component_sizes
        )
    )

    if largest_component_label <= 0:
        raise RuntimeError(
            "Could not identify the "
            "largest foreground component"
        )

    largest_component = np.asarray(
        component_labels
        == largest_component_label,
        dtype=bool,
    )

    largest_component_voxels = int(
        np.count_nonzero(
            largest_component
        )
    )

    if largest_component_voxels == 0:
        raise RuntimeError(
            "Largest foreground "
            "component is empty"
        )

    fill_result = (
        binary_fill_holes(
            largest_component
        )
    )

    cleaned = np.asarray(
        fill_result,
        dtype=bool,
    )

    cleaned_voxels = int(
        np.count_nonzero(
            cleaned
        )
    )

    if cleaned_voxels == 0:
        raise RuntimeError(
            "Registration-mask cleanup "
            "produced an empty mask"
        )

    removed_voxels = max(
        0,
        (
            original_voxels
            - largest_component_voxels
        ),
    )

    retained_fraction = float(
        largest_component_voxels
        / original_voxels
    )

    report = RegistrationMaskReport(
        original_voxels=(
            original_voxels
        ),
        cleaned_voxels=(
            cleaned_voxels
        ),
        component_count=(
            component_count
        ),
        removed_voxels=(
            removed_voxels
        ),
        retained_fraction=(
            retained_fraction
        ),
    )

    return RegistrationMaskResult(
        mask=(
            cleaned
        ),
        report=(
            report
        ),
    )