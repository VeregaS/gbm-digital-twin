from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.scene3d import (
    SurfaceMesh,
    Viewer3DScene,
)


class SurfaceMeshResponse(BaseModel):
    name: str

    vertices: list[float]
    triangles: list[int]

    vertex_count: int
    triangle_count: int

    bounds: tuple[
        float,
        float,
        float,
        float,
        float,
        float,
    ]

    @classmethod
    def from_mesh(
        cls,
        mesh: SurfaceMesh,
    ) -> SurfaceMeshResponse:
        return cls(
            name=mesh.name,
            vertices=(
                mesh.vertices
                .reshape(-1)
                .tolist()
            ),
            triangles=(
                mesh.triangles
                .reshape(-1)
                .tolist()
            ),
            vertex_count=(
                mesh.vertex_count
            ),
            triangle_count=(
                mesh.triangle_count
            ),
            bounds=mesh.bounds,
        )


class Viewer3DSceneResponse(BaseModel):
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

    brain: SurfaceMeshResponse
    gtv: SurfaceMeshResponse

    latent_outer: SurfaceMeshResponse
    latent_core: SurfaceMeshResponse

    @classmethod
    def from_scene(
        cls,
        scene: Viewer3DScene,
    ) -> Viewer3DSceneResponse:
        return cls(
            patient_id=(
                scene.patient_id
            ),
            timepoint_name=(
                scene.timepoint_name
            ),
            spacing=scene.spacing,
            latent_width_mm=(
                scene.latent_width_mm
            ),
            latent_outer_level=(
                scene.latent_outer_level
            ),
            latent_core_level=(
                scene.latent_core_level
            ),
            brain=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.brain
                )
            ),
            gtv=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.gtv
                )
            ),
            latent_outer=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.latent_outer
                )
            ),
            latent_core=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.latent_core
                )
            ),
        )