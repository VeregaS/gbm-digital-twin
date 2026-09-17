from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.api.schemas.scene3d import (
    SurfaceMeshResponse,
)
from gbm_twin.workflows.twin_scene3d import (
    TwinViewer3DScene,
)


class TwinViewer3DSceneResponse(
    BaseModel
):
    patient_id: int
    timepoint_name: str

    spacing: tuple[
        float,
        float,
        float,
    ]

    brain: SurfaceMeshResponse
    observed: SurfaceMeshResponse

    twin: SurfaceMeshResponse
    persistence: SurfaceMeshResponse

    volume_baseline: (
        SurfaceMeshResponse
    )

    @classmethod
    def from_scene(
        cls,
        scene: TwinViewer3DScene,
    ) -> TwinViewer3DSceneResponse:
        return cls(
            patient_id=(
                scene.patient_id
            ),
            timepoint_name=(
                scene.timepoint_name
            ),
            spacing=scene.spacing,
            brain=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.brain
                )
            ),
            observed=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.observed
                )
            ),
            twin=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.twin
                )
            ),
            persistence=(
                SurfaceMeshResponse
                .from_mesh(
                    scene.persistence
                )
            ),
            volume_baseline=(
                SurfaceMeshResponse
                .from_mesh(
                    scene
                    .volume_baseline
                )
            ),
        )