from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.viewer_focus import (
    ViewerFocusMetadata,
)


class ViewerFocusResponse(BaseModel):
    patient_id: int
    timepoint_name: str

    axial_index: int | None
    coronal_index: int | None
    sagittal_index: int | None

    gtv_voxels: int

    @classmethod
    def from_metadata(
        cls,
        metadata: ViewerFocusMetadata,
    ) -> ViewerFocusResponse:
        return cls(
            patient_id=(
                metadata.patient_id
            ),
            timepoint_name=(
                metadata.timepoint_name
            ),
            axial_index=(
                metadata.axial_index
            ),
            coronal_index=(
                metadata.coronal_index
            ),
            sagittal_index=(
                metadata.sagittal_index
            ),
            gtv_voxels=(
                metadata.gtv_voxels
            ),
        )
