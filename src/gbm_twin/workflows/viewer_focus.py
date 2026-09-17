from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    prepare_patient_timepoint,
)

BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class ViewerFocusMetadata:
    patient_id: int
    timepoint_name: str

    axial_index: int | None
    coronal_index: int | None
    sagittal_index: int | None

    gtv_voxels: int


def _peak_slice_index(
    mask: BoolArray,
    *,
    axis: int,
) -> int | None:
    if mask.ndim != 3:
        raise ValueError(
            f"Expected 3D GTV mask, got shape {mask.shape}"
        )

    if axis not in {
        0,
        1,
        2,
    }:
        raise ValueError(
            f"Unsupported GTV focus axis: {axis}"
        )

    if not np.any(mask):
        return None

    reduce_axes = tuple(
        index
        for index in range(3)
        if index != axis
    )

    areas = np.sum(
        mask,
        axis=reduce_axes,
        dtype=np.int64,
    )

    peak_area = int(
        np.max(areas)
    )

    candidate_indices = np.flatnonzero(
        areas == peak_area
    )

    if candidate_indices.size == 0:
        return None

    middle_candidate = (
        candidate_indices.size // 2
    )

    return int(
        candidate_indices[
            middle_candidate
        ]
    )


@lru_cache(maxsize=24)
def _get_viewer_focus_cached(
    metadata_root_text: str,
    patients_root_text: str,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ],
) -> ViewerFocusMetadata:
    normalized_name = (
        timepoint_name
        .strip()
        .lower()
    )

    if normalized_name not in {
        "t0",
        "t1",
        "t2",
    }:
        raise ValueError(
            "timepoint_name must be t0, t1 or t2"
        )

    prepared = prepare_patient_timepoint(
        metadata_root=Path(
            metadata_root_text
        ),
        patients_root=Path(
            patients_root_text
        ),
        patient_id=patient_id,
        timepoint_name=normalized_name,
        target_spacing=target_spacing,
    )

    mask: BoolArray = np.asarray(
        prepared.gtv.data
        > 0.5,
        dtype=np.bool_,
    )

    return ViewerFocusMetadata(
        patient_id=patient_id,
        timepoint_name=normalized_name,
        axial_index=(
            _peak_slice_index(
                mask,
                axis=2,
            )
        ),
        coronal_index=(
            _peak_slice_index(
                mask,
                axis=1,
            )
        ),
        sagittal_index=(
            _peak_slice_index(
                mask,
                axis=0,
            )
        ),
        gtv_voxels=int(
            np.count_nonzero(mask)
        ),
    )


def clear_viewer_focus_cache() -> None:
    _get_viewer_focus_cached.cache_clear()


def get_viewer_focus_metadata(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ] = DEFAULT_TARGET_SPACING,
) -> ViewerFocusMetadata:
    return _get_viewer_focus_cached(
        str(metadata_root.resolve()),
        str(patients_root.resolve()),
        patient_id,
        timepoint_name,
        target_spacing,
    )
