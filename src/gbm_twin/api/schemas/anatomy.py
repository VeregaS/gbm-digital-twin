from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.anatomy.models import (
    AnatomicalRiskReport,
)


class AnatomicalWarningResponse(
    BaseModel
):
    severity: str

    region_label: int
    region_name: str
    category: str

    laterality: str | None
    functional_note: str | None

    observed_overlap_cm3: float
    latent_overlap_cm3: float

    min_observed_distance_mm: (
        float | None
    )

    message: str


class AnatomicalRiskResponse(
    BaseModel
):
    patient_id: int
    timepoint_name: str

    configured: bool

    atlas_name: str | None
    status_message: str

    latent_level: float
    proximity_threshold_mm: float

    high_count: int
    moderate_count: int

    warnings: list[
        AnatomicalWarningResponse
    ]

    disclaimer: str

    @classmethod
    def from_report(
        cls,
        report: AnatomicalRiskReport,
    ) -> AnatomicalRiskResponse:
        return cls(
            patient_id=(
                report.patient_id
            ),
            timepoint_name=(
                report.timepoint_name
            ),
            configured=(
                report.configured
            ),
            atlas_name=(
                report.atlas_name
            ),
            status_message=(
                report.status_message
            ),
            latent_level=(
                report.latent_level
            ),
            proximity_threshold_mm=(
                report
                .proximity_threshold_mm
            ),
            high_count=(
                report.high_count
            ),
            moderate_count=(
                report.moderate_count
            ),
            warnings=[
                AnatomicalWarningResponse(
                    severity=(
                        warning.severity
                    ),
                    region_label=(
                        warning.region_label
                    ),
                    region_name=(
                        warning.region_name
                    ),
                    category=(
                        warning.category
                    ),
                    laterality=(
                        warning.laterality
                    ),
                    functional_note=(
                        warning.functional_note
                    ),
                    observed_overlap_cm3=(
                        warning
                        .observed_overlap_cm3
                    ),
                    latent_overlap_cm3=(
                        warning
                        .latent_overlap_cm3
                    ),
                    min_observed_distance_mm=(
                        warning
                        .min_observed_distance_mm
                    ),
                    message=(
                        warning.message
                    ),
                )
                for warning
                in report.warnings
            ],
            disclaimer=(
                report.disclaimer
            ),
        )