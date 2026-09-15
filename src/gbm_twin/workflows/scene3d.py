from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.measure import marching_cubes

from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    prepare_patient_timepoint,
)

LATENT_WIDTH_MM = 4.0

LATENT_OUTER_LEVEL = 0.2
LATENT_CORE_LEVEL = 0.8


@dataclass(frozen=True)
class SurfaceMesh:
    name: str

    vertices: np.ndarray
    triangles: np.ndarray

    bounds: tuple[
        float,
        float,
        float,
        float,
        float,
        float,
    ]

    @property
    def vertex_count(self) -> int:
        return int(
            self.vertices.shape[0]
        )

    @property
    def triangle_count(self) -> int:
        return int(
            self.triangles.shape[0]
        )


@dataclass(frozen=True)
class Viewer3DScene:
    patient_id: int
    timepoint_name: str

    spacing: tuple[
        float,
        float,
        float,
    ]

    latent_width_mm: float
    latent_outer_level: float
    latent_core_level: float

    brain: SurfaceMesh
    gtv: SurfaceMesh

    latent_outer: SurfaceMesh
    latent_core: SurfaceMesh


def _empty_mesh(
    name: str,
) -> SurfaceMesh:
    return SurfaceMesh(
        name=name,
        vertices=np.empty(
            (0, 3),
            dtype=np.float32,
        ),
        triangles=np.empty(
            (0, 3),
            dtype=np.uint32,
        ),
        bounds=(
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ),
    )


def _mesh_bounds(
    vertices: np.ndarray,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    if vertices.shape[0] == 0:
        return (
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )

    minimum = np.min(
        vertices,
        axis=0,
    )

    maximum = np.max(
        vertices,
        axis=0,
    )

    return (
        float(minimum[0]),
        float(maximum[0]),
        float(minimum[1]),
        float(maximum[1]),
        float(minimum[2]),
        float(maximum[2]),
    )


def surface_mesh_from_scalar_field(
    field: np.ndarray,
    *,
    level: float,
    spacing: tuple[
        float,
        float,
        float,
    ],
    name: str,
    step_size: int = 1,
) -> SurfaceMesh:
    if field.ndim != 3:
        raise ValueError(
            f"Expected 3D field, "
            f"got shape {field.shape}"
        )

    if step_size <= 0:
        raise ValueError(
            "step_size must be positive"
        )

    if not np.isfinite(level):
        raise ValueError(
            "level must be finite"
        )

    scalar = np.asarray(
        field,
        dtype=np.float32,
    )

    scalar = np.nan_to_num(
        scalar,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    minimum = float(
        np.min(scalar)
    )

    maximum = float(
        np.max(scalar)
    )

    if not (
        minimum < level < maximum
    ):
        return _empty_mesh(
            name
        )

    padded = np.pad(
        scalar,
        pad_width=2,
        mode="constant",
        constant_values=0.0,
    )

    vertices, faces, _, _ = (
        marching_cubes(
            padded,
            level=level,
            spacing=spacing,
            step_size=step_size,
            allow_degenerate=False,
        )
    )

    padding_offset = (
        np.asarray(
            spacing,
            dtype=np.float32,
        )
        * 2.0
    )

    vertices = (
        vertices.astype(
            np.float32,
            copy=False,
        )
        - padding_offset
    )

    faces = faces.astype(
        np.uint32,
        copy=False,
    )

    return SurfaceMesh(
        name=name,
        vertices=vertices,
        triangles=faces,
        bounds=_mesh_bounds(
            vertices
        ),
    )


def _visual_surface_field(
    mask: np.ndarray,
    *,
    smoothing_sigma_voxels: float,
) -> np.ndarray:
    binary = np.asarray(
        mask,
        dtype=np.float32,
    )

    if smoothing_sigma_voxels <= 0:
        return binary

    smoothed = gaussian_filter(
        binary,
        sigma=smoothing_sigma_voxels,
        mode="constant",
        cval=0.0,
    )

    return np.asarray(
        smoothed,
        dtype=np.float32,
    )


def surface_mesh_from_mask(
    mask: np.ndarray,
    *,
    spacing: tuple[
        float,
        float,
        float,
    ],
    name: str,
    step_size: int = 1,
    smoothing_sigma_voxels: float = 0.0,
) -> SurfaceMesh:
    if mask.ndim != 3:
        raise ValueError(
            f"Expected 3D mask, "
            f"got shape {mask.shape}"
        )

    if step_size <= 0:
        raise ValueError(
            "step_size must be positive"
        )

    if smoothing_sigma_voxels < 0:
        raise ValueError(
            "smoothing_sigma_voxels "
            "must be non-negative"
        )

    binary = np.asarray(
        mask,
        dtype=bool,
    )

    if not np.any(binary):
        return _empty_mesh(
            name
        )

    field = _visual_surface_field(
        binary,
        smoothing_sigma_voxels=(
            smoothing_sigma_voxels
        ),
    )

    return surface_mesh_from_scalar_field(
        field,
        level=0.5,
        spacing=spacing,
        name=name,
        step_size=step_size,
    )


@lru_cache(maxsize=4)
def _build_scene_cached(
    metadata_root_text: str,
    patients_root_text: str,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ],
) -> Viewer3DScene:
    prepared = (
        prepare_patient_timepoint(
            metadata_root=Path(
                metadata_root_text
            ),
            patients_root=Path(
                patients_root_text
            ),
            patient_id=patient_id,
            timepoint_name=(
                timepoint_name
            ),
            target_spacing=(
                target_spacing
            ),
        )
    )

    brain_mask = (
        np.asarray(
            prepared.brain_mask.data
        )
        > 0.5
    )

    gtv_mask = (
        np.asarray(
            prepared.gtv.data
        )
        > 0.5
    )

    brain = surface_mesh_from_mask(
        brain_mask,
        spacing=prepared.spacing,
        name="brain",
        step_size=1,
        smoothing_sigma_voxels=1.15,
    )

    gtv = surface_mesh_from_mask(
        gtv_mask,
        spacing=prepared.spacing,
        name="gtv",
        step_size=1,
        smoothing_sigma_voxels=0.25,
    )

    latent = latent_state_from_gtv(
        prepared.gtv.data,
        prepared.brain_mask.data,
        spacing=prepared.spacing,
        parameters=LatentStateParameters(
            transition_width_mm=(
                LATENT_WIDTH_MM
            ),
        ),
    )

    latent_outer = (
        surface_mesh_from_scalar_field(
            latent,
            level=LATENT_OUTER_LEVEL,
            spacing=prepared.spacing,
            name="latent_outer",
            step_size=1,
        )
    )

    latent_core = (
        surface_mesh_from_scalar_field(
            latent,
            level=LATENT_CORE_LEVEL,
            spacing=prepared.spacing,
            name="latent_core",
            step_size=1,
        )
    )

    return Viewer3DScene(
        patient_id=patient_id,
        timepoint_name=(
            timepoint_name
        ),
        spacing=prepared.spacing,
        latent_width_mm=(
            LATENT_WIDTH_MM
        ),
        latent_outer_level=(
            LATENT_OUTER_LEVEL
        ),
        latent_core_level=(
            LATENT_CORE_LEVEL
        ),
        brain=brain,
        gtv=gtv,
        latent_outer=latent_outer,
        latent_core=latent_core,
    )


def get_viewer_3d_scene(
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
) -> Viewer3DScene:
    normalized_timepoint = (
        timepoint_name
        .strip()
        .lower()
    )

    if normalized_timepoint not in {
        "t0",
        "t1",
        "t2",
    }:
        raise ValueError(
            "timepoint_name must be "
            "t0, t1 or t2"
        )

    return _build_scene_cached(
        str(
            metadata_root.resolve()
        ),
        str(
            patients_root.resolve()
        ),
        patient_id,
        normalized_timepoint,
        target_spacing,
    )


def clear_scene_3d_cache() -> None:
    _build_scene_cached.cache_clear()