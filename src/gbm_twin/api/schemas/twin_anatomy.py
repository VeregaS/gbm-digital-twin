from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.twin_anatomy import (
    TwinAnatomicalImpactReport,
)


class TwinAtlasReviewResponse(
    BaseModel
):
    timepoint_name: str
    verified: bool
    decision: str | None
    automatic_qc_status: str | None
    reviewed_at_utc: str | None
    status_message: str


class TwinAnatomicalRegionImpactResponse(
    BaseModel
):
    severity: str
    region_label: int
    region_name: str
    category: str
    laterality: str | None
    functional_note: str | None
    mask_overlap_cm3: float
    density_overlap_cm3: float
    min_distance_mm: float | None


class TwinAnatomicalChangeResponse(
    BaseModel
):
    status: str
    region_label: int
    region_name: str
    category: str
    laterality: str | None
    functional_note: str | None
    current_severity: str | None
    forecast_severity: str | None


class TwinAnatomicalImpactResponse(
    BaseModel
):
    patient_id: int
    current_timepoint: str
    forecast_timepoint: str
    configured: bool
    atlas_name: str | None
    status_message: str
    registration: TwinAtlasReviewResponse
    current: list[
        TwinAnatomicalRegionImpactResponse
    ]
    forecast: list[
        TwinAnatomicalRegionImpactResponse
    ]
    changes: list[
        TwinAnatomicalChangeResponse
    ]
    latent_level: float
    proximity_threshold_mm: float
    disclaimer: str

    @classmethod
    def from_report(
        cls,
        report: TwinAnatomicalImpactReport,
    ) -> TwinAnatomicalImpactResponse:
        return cls.model_validate(
            report,
            from_attributes=True,
        )
