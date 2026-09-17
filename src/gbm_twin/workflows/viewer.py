from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    PreparedPatientTimepoint,
    prepare_patient_timepoint,
)

ViewerPlane = Literal[
    "axial",
    "coronal",
    "sagittal",
]


@dataclass(frozen=True)
class ViewerPlaneMetadata:
    name: ViewerPlane

    size: int
    max_index: int
    default_index: int

    image_width: int
    image_height: int


@dataclass(frozen=True)
class ViewerVolumeMetadata:
    patient_id: int
    timepoint_name: str

    shape: tuple[
        int,
        int,
        int,
    ]

    spacing: tuple[
        float,
        float,
        float,
    ]

    intensity_low: float
    intensity_high: float

    gtv_voxels: int
    gtv_volume_cm3: float

    planes: tuple[
        ViewerPlaneMetadata,
        ...,
    ]


@dataclass(frozen=True)
class _CachedViewerVolume:
    prepared: PreparedPatientTimepoint

    intensity_low: float
    intensity_high: float


def _calculate_intensity_window(
    prepared: PreparedPatientTimepoint,
) -> tuple[float, float]:
    image = np.asarray(
        prepared.t1gd.data,
        dtype=np.float32,
    )

    brain = (
        np.asarray(
            prepared.brain_mask.data
        )
        > 0.5
    )

    if np.any(brain):
        values = image[brain]
    else:
        values = image.reshape(-1)

    finite = values[
        np.isfinite(values)
    ]

    if finite.size == 0:
        return (
            0.0,
            1.0,
        )

    low = float(
        np.percentile(
            finite,
            1.0,
        )
    )

    high = float(
        np.percentile(
            finite,
            99.0,
        )
    )

    if high <= low:
        low = float(
            np.min(finite)
        )

        high = float(
            np.max(finite)
        )

    if high <= low:
        high = low + 1.0

    return (
        low,
        high,
    )


@lru_cache(maxsize=8)
def _load_cached_viewer_volume(
    metadata_root_text: str,
    patients_root_text: str,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ],
) -> _CachedViewerVolume:
    prepared = prepare_patient_timepoint(
        metadata_root=Path(
            metadata_root_text
        ),
        patients_root=Path(
            patients_root_text
        ),
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        target_spacing=target_spacing,
    )

    low, high = (
        _calculate_intensity_window(
            prepared
        )
    )

    return _CachedViewerVolume(
        prepared=prepared,
        intensity_low=low,
        intensity_high=high,
    )


def clear_viewer_cache() -> None:
    _load_cached_viewer_volume.cache_clear()


def _load_viewer_volume(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ],
) -> _CachedViewerVolume:
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
            "timepoint_name must be "
            "t0, t1 or t2"
        )

    return _load_cached_viewer_volume(
        str(metadata_root.resolve()),
        str(patients_root.resolve()),
        patient_id,
        normalized_name,
        target_spacing,
    )


def _plane_metadata(
    shape: tuple[
        int,
        int,
        int,
    ],
) -> tuple[
    ViewerPlaneMetadata,
    ...,
]:
    x_size, y_size, z_size = shape

    return (
        ViewerPlaneMetadata(
            name="axial",
            size=z_size,
            max_index=z_size - 1,
            default_index=z_size // 2,
            image_width=x_size,
            image_height=y_size,
        ),
        ViewerPlaneMetadata(
            name="coronal",
            size=y_size,
            max_index=y_size - 1,
            default_index=y_size // 2,
            image_width=x_size,
            image_height=z_size,
        ),
        ViewerPlaneMetadata(
            name="sagittal",
            size=x_size,
            max_index=x_size - 1,
            default_index=x_size // 2,
            image_width=y_size,
            image_height=z_size,
        ),
    )


def get_viewer_volume_metadata(
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
) -> ViewerVolumeMetadata:
    cached = _load_viewer_volume(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        target_spacing=target_spacing,
    )

    prepared = cached.prepared

    shape = tuple(
        int(value)
        for value in prepared.t1gd.data.shape
    )

    if len(shape) != 3:
        raise ValueError(
            f"Expected 3D MRI volume, "
            f"got shape {shape}"
        )

    shape_3d = (
        shape[0],
        shape[1],
        shape[2],
    )

    gtv = (
        np.asarray(
            prepared.gtv.data
        )
        > 0.5
    )

    gtv_voxels = int(
        np.count_nonzero(gtv)
    )

    voxel_volume_mm3 = float(
        prepared.spacing[0]
        * prepared.spacing[1]
        * prepared.spacing[2]
    )

    gtv_volume_cm3 = (
        gtv_voxels
        * voxel_volume_mm3
        / 1000.0
    )

    return ViewerVolumeMetadata(
        patient_id=patient_id,
        timepoint_name=(
            timepoint_name
            .strip()
            .lower()
        ),
        shape=shape_3d,
        spacing=prepared.spacing,
        intensity_low=(
            cached.intensity_low
        ),
        intensity_high=(
            cached.intensity_high
        ),
        gtv_voxels=gtv_voxels,
        gtv_volume_cm3=float(
            gtv_volume_cm3
        ),
        planes=_plane_metadata(
            shape_3d
        ),
    )


def _extract_plane(
    volume: np.ndarray,
    *,
    plane: ViewerPlane,
    index: int,
) -> np.ndarray:
    if volume.ndim != 3:
        raise ValueError(
            f"Expected 3D volume, "
            f"got shape {volume.shape}"
        )

    if plane == "axial":
        max_index = (
            volume.shape[2] - 1
        )

        if not (
            0 <= index <= max_index
        ):
            raise IndexError(
                f"Axial index {index} "
                f"is outside 0..{max_index}"
            )

        result = volume[
            :,
            :,
            index,
        ].T

    elif plane == "coronal":
        max_index = (
            volume.shape[1] - 1
        )

        if not (
            0 <= index <= max_index
        ):
            raise IndexError(
                f"Coronal index {index} "
                f"is outside 0..{max_index}"
            )

        result = volume[
            :,
            index,
            :,
        ].T

    elif plane == "sagittal":
        max_index = (
            volume.shape[0] - 1
        )

        if not (
            0 <= index <= max_index
        ):
            raise IndexError(
                f"Sagittal index {index} "
                f"is outside 0..{max_index}"
            )

        result = volume[
            index,
            :,
            :,
        ].T

    else:
        raise ValueError(
            f"Unsupported plane: {plane}"
        )

    return np.flipud(
        np.asarray(result)
    )


def _normalize_mri_slice(
    image: np.ndarray,
    *,
    low: float,
    high: float,
) -> np.ndarray:
    image_float = np.asarray(
        image,
        dtype=np.float32,
    )

    image_float = np.nan_to_num(
        image_float,
        nan=low,
        posinf=high,
        neginf=low,
    )

    normalized = (
        image_float - low
    ) / (
        high - low
    )

    normalized = np.clip(
        normalized,
        0.0,
        1.0,
    )

    return (
        normalized * 255.0
    ).astype(
        np.uint8
    )


def render_viewer_slice_png(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    plane: ViewerPlane,
    index: int | None = None,
    overlay_gtv: bool = True,
    target_spacing: tuple[
        float,
        float,
        float,
    ] = DEFAULT_TARGET_SPACING,
) -> bytes:
    cached = _load_viewer_volume(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        target_spacing=target_spacing,
    )

    prepared = cached.prepared

    metadata = (
        get_viewer_volume_metadata(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=(
                timepoint_name
            ),
            target_spacing=(
                target_spacing
            ),
        )
    )

    plane_metadata = next(
        item
        for item in metadata.planes
        if item.name == plane
    )

    slice_index = (
        plane_metadata.default_index
        if index is None
        else index
    )

    image_slice = _extract_plane(
        prepared.t1gd.data,
        plane=plane,
        index=slice_index,
    )

    grayscale = _normalize_mri_slice(
        image_slice,
        low=cached.intensity_low,
        high=cached.intensity_high,
    )

    rgb = np.repeat(
        grayscale[
            :,
            :,
            np.newaxis,
        ],
        3,
        axis=2,
    ).astype(
        np.float32
    )

    if overlay_gtv:
        mask_slice = _extract_plane(
            np.asarray(
                prepared.gtv.data
            ),
            plane=plane,
            index=slice_index,
        )

        mask = (
            mask_slice > 0.5
        )

        if np.any(mask):
            overlay_color = np.array(
                [
                    235.0,
                    111.0,
                    74.0,
                ],
                dtype=np.float32,
            )

            alpha = 0.45

            rgb[mask] = (
                (1.0 - alpha)
                * rgb[mask]
                + alpha
                * overlay_color
            )

    rgb_uint8 = np.clip(
        rgb,
        0.0,
        255.0,
    ).astype(
        np.uint8
    )

    image = Image.fromarray(
        rgb_uint8
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()

def render_viewer_mask_slice_png(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    overlay_mask: np.ndarray,
    plane: ViewerPlane,
    index: int | None = None,
    overlay_color: tuple[
        float,
        float,
        float,
    ] = (
        37.0,
        99.0,
        235.0,
    ),
    overlay_alpha: float = 0.50,
    target_spacing: tuple[
        float,
        float,
        float,
    ] = DEFAULT_TARGET_SPACING,
) -> bytes:
    if not (
        0.0
        <= overlay_alpha
        <= 1.0
    ):
        raise ValueError(
            "overlay_alpha must be "
            "within [0, 1]"
        )

    cached = _load_viewer_volume(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        target_spacing=target_spacing,
    )

    prepared = cached.prepared

    mask_volume = np.asarray(
        overlay_mask
    )

    if (
        mask_volume.shape
        != prepared.t1gd.data.shape
    ):
        raise ValueError(
            "Overlay mask shape does not "
            "match MRI geometry: "
            f"{mask_volume.shape} vs "
            f"{prepared.t1gd.data.shape}"
        )

    metadata = (
        get_viewer_volume_metadata(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=timepoint_name,
            target_spacing=target_spacing,
        )
    )

    plane_metadata = next(
        item
        for item in metadata.planes
        if item.name == plane
    )

    slice_index = (
        plane_metadata.default_index
        if index is None
        else index
    )

    image_slice = _extract_plane(
        prepared.t1gd.data,
        plane=plane,
        index=slice_index,
    )

    grayscale = _normalize_mri_slice(
        image_slice,
        low=cached.intensity_low,
        high=cached.intensity_high,
    )

    rgb = np.repeat(
        grayscale[
            :,
            :,
            np.newaxis,
        ],
        3,
        axis=2,
    ).astype(
        np.float32
    )

    mask_slice = _extract_plane(
        mask_volume,
        plane=plane,
        index=slice_index,
    )

    mask = (
        mask_slice
        > 0.5
    )

    if np.any(mask):
        color = np.asarray(
            overlay_color,
            dtype=np.float32,
        )

        rgb[mask] = (
            (1.0 - overlay_alpha)
            * rgb[mask]
            + overlay_alpha
            * color
        )

    rgb_uint8 = np.clip(
        rgb,
        0.0,
        255.0,
    ).astype(
        np.uint8
    )

    image = Image.fromarray(
        rgb_uint8
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()