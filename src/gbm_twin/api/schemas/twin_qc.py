from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.twin_qc import (
    TwinMaskQC,
    TwinPatientQC,
    TwinQCWarning,
)


class TwinMaskQCResponse(
    BaseModel
):
    name: str

    voxel_count: int
    volume_cm3: float

    component_count: int

    largest_component_fraction: (
        float | None
    )

    outside_brain_voxels: int

    outside_brain_fraction: (
        float | None
    )

    centroid_inside_brain: (
        bool | None
    )

    @classmethod
    def from_qc(
        cls,
        qc: TwinMaskQC,
    ) -> TwinMaskQCResponse:
        return cls(
            name=qc.name,
            voxel_count=(
                qc.voxel_count
            ),
            volume_cm3=(
                qc.volume_cm3
            ),
            component_count=(
                qc.component_count
            ),
            largest_component_fraction=(
                qc
                .largest_component_fraction
            ),
            outside_brain_voxels=(
                qc.outside_brain_voxels
            ),
            outside_brain_fraction=(
                qc
                .outside_brain_fraction
            ),
            centroid_inside_brain=(
                qc
                .centroid_inside_brain
            ),
        )


class TwinQCWarningResponse(
    BaseModel
):
    code: str
    message: str

    @classmethod
    def from_warning(
        cls,
        warning: TwinQCWarning,
    ) -> TwinQCWarningResponse:
        return cls(
            code=warning.code.value,
            message=warning.message,
        )


class TwinPatientQCResponse(
    BaseModel
):
    patient_id: int

    observed: TwinMaskQCResponse
    twin: TwinMaskQCResponse
    persistence: TwinMaskQCResponse

    volume_baseline: (
        TwinMaskQCResponse
    )

    warnings: list[
        TwinQCWarningResponse
    ]

    @classmethod
    def from_qc(
        cls,
        qc: TwinPatientQC,
    ) -> TwinPatientQCResponse:
        return cls(
            patient_id=(
                qc.patient_id
            ),
            observed=(
                TwinMaskQCResponse
                .from_qc(
                    qc.observed
                )
            ),
            twin=(
                TwinMaskQCResponse
                .from_qc(
                    qc.twin
                )
            ),
            persistence=(
                TwinMaskQCResponse
                .from_qc(
                    qc.persistence
                )
            ),
            volume_baseline=(
                TwinMaskQCResponse
                .from_qc(
                    qc.volume_baseline
                )
            ),
            warnings=[
                TwinQCWarningResponse
                .from_warning(
                    warning
                )
                for warning
                in qc.warnings
            ],
        )