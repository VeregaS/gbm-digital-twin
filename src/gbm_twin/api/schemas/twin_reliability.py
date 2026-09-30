from __future__ import annotations

from pydantic import BaseModel

from gbm_twin.workflows.twin_reliability import (
    TwinForecastReliability,
)


class TwinForecastReliabilityFactorResponse(
    BaseModel
):
    code: str
    level: str
    message: str


class TwinForecastReliabilityResponse(
    BaseModel
):
    patient_id: int
    status: str
    model_version: str
    protocol_version: str
    sealed: bool
    source_git_commit_sha: str
    source_git_dirty: bool
    forecast_horizon_days: float
    calibration_identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool
    prediction_empty: bool
    prediction_component_count: int
    prediction_largest_component_fraction: float | None
    prediction_outside_brain_fraction: float | None
    factors: list[
        TwinForecastReliabilityFactorResponse
    ]
    interpretation: str

    @classmethod
    def from_reliability(
        cls,
        reliability: TwinForecastReliability,
    ) -> TwinForecastReliabilityResponse:
        return cls.model_validate(
            reliability,
            from_attributes=True,
        )
