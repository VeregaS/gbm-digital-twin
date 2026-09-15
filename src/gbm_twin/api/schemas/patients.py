from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.patient_catalog import (
    PatientCatalogSummary,
)


class PatientListItemResponse(BaseModel):
    patient_id: int
    label: str


class PatientListResponse(BaseModel):
    patients: list[
        PatientListItemResponse
    ]


class PatientTimepointResponse(BaseModel):
    name: str
    days_from_baseline: float | None

    gtv_available: bool | None
    gtv_type: str | None

    rtdose_available: bool | None


class PatientTreatmentResponse(BaseModel):
    has_record: bool

    rt_start_day: float | None
    rt_start_phase: str

    rt_started_by_t1: bool | None
    rt_started_by_t2: bool | None

    dose_gy: float | None
    fractions: int | None

    reconstructable: bool


class PatientSummaryResponse(BaseModel):
    patient_id: int

    timepoints: list[
        PatientTimepointResponse
    ]

    timepoint_count: int

    dt01_days: float | None
    dt12_days: float | None

    treatment: PatientTreatmentResponse

    @classmethod
    def from_summary(
        cls,
        summary: PatientCatalogSummary,
    ) -> PatientSummaryResponse:
        return cls(
            patient_id=summary.patient_id,
            timepoints=[
                PatientTimepointResponse(
                    name=timepoint.name,
                    days_from_baseline=(
                        timepoint.days_from_baseline
                    ),
                    gtv_available=(
                        timepoint.gtv_available
                    ),
                    gtv_type=(
                        timepoint.gtv_type
                    ),
                    rtdose_available=(
                        timepoint.rtdose_available
                    ),
                )
                for timepoint
                in summary.timepoints
            ],
            timepoint_count=(
                summary.timepoint_count
            ),
            dt01_days=summary.dt01_days,
            dt12_days=summary.dt12_days,
            treatment=(
                PatientTreatmentResponse(
                    has_record=(
                        summary.treatment.has_record
                    ),
                    rt_start_day=(
                        summary.treatment.rt_start_day
                    ),
                    rt_start_phase=(
                        summary.treatment.rt_start_phase
                    ),
                    rt_started_by_t1=(
                        summary.treatment.rt_started_by_t1
                    ),
                    rt_started_by_t2=(
                        summary.treatment.rt_started_by_t2
                    ),
                    dose_gy=(
                        summary.treatment.dose_gy
                    ),
                    fractions=(
                        summary.treatment.fractions
                    ),
                    reconstructable=(
                        summary.treatment.reconstructable
                    ),
                )
            ),
        )