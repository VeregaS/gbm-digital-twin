from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.viewer import (
    ViewerVolumeMetadata,
)


class ViewerPlaneResponse(BaseModel):
    name: str

    size: int
    max_index: int
    default_index: int

    image_width: int
    image_height: int


class ViewerVolumeResponse(BaseModel):
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

    planes: list[
        ViewerPlaneResponse
    ]

    @classmethod
    def from_metadata(
        cls,
        metadata: ViewerVolumeMetadata,
    ) -> ViewerVolumeResponse:
        return cls(
            patient_id=(
                metadata.patient_id
            ),
            timepoint_name=(
                metadata.timepoint_name
            ),
            shape=metadata.shape,
            spacing=metadata.spacing,
            intensity_low=(
                metadata.intensity_low
            ),
            intensity_high=(
                metadata.intensity_high
            ),
            gtv_voxels=(
                metadata.gtv_voxels
            ),
            gtv_volume_cm3=(
                metadata.gtv_volume_cm3
            ),
            planes=[
                ViewerPlaneResponse(
                    name=plane.name,
                    size=plane.size,
                    max_index=(
                        plane.max_index
                    ),
                    default_index=(
                        plane.default_index
                    ),
                    image_width=(
                        plane.image_width
                    ),
                    image_height=(
                        plane.image_height
                    ),
                )
                for plane
                in metadata.planes
            ],
        )