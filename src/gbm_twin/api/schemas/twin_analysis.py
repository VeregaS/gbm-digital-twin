from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from gbm_twin.api.schemas.twin import (
    TwinDatasetResponse,
    TwinRepositoryResponse,
)

TrajectoryResponse = Literal[
    "growth",
    "stable",
    "regression",
    "unknown",
]


class TwinAnalysisConfigResponse(BaseModel):
    stable_volume_change_fraction: float
    worst_patient_count: int
    min_correlation_patients: int


class TwinCorrelationResponse(BaseModel):
    count: int
    pearson: float | None
    spearman: float | None


class TwinTrajectoryGroupResponse(BaseModel):
    trajectory: TrajectoryResponse
    patient_count: int
    mean_twin_dice: float | None
    mean_delta_vs_persistence: float | None
    mean_hd95_mm: float | None


class TwinCohortErrorSummaryResponse(BaseModel):
    patient_count: int

    mean_twin_dice: float | None
    median_twin_dice: float | None

    mean_delta_vs_persistence: float | None
    median_delta_vs_persistence: float | None

    mean_delta_vs_volume_baseline: float | None
    median_delta_vs_volume_baseline: float | None

    twin_better_than_persistence_count: int
    twin_equal_to_persistence_count: int
    twin_worse_than_persistence_count: int

    twin_better_than_volume_baseline_count: int
    twin_equal_to_volume_baseline_count: int
    twin_worse_than_volume_baseline_count: int

    qc_flagged_count: int
    calibration_non_identifiable_count: int
    calibration_boundary_count: int

    worst_twin_dice_patient_ids: list[int]
    worst_delta_vs_persistence_patient_ids: list[int]

    forecast_horizon_vs_twin_dice: TwinCorrelationResponse
    volume_change_t1_t2_vs_twin_dice: TwinCorrelationResponse
    calibration_dice_vs_twin_dice: TwinCorrelationResponse

    trajectory_groups: list[
        TwinTrajectoryGroupResponse
    ]


class TwinCohortPatientErrorResponse(BaseModel):
    patient_id: int

    calibration_days: float | None
    forecast_horizon_days: float | None
    target_day: float

    rt_start_day: float | None
    rt_started_by_t1: bool | None
    treatment_reconstructable: bool

    volume_t0_cm3: float
    volume_t1_cm3: float
    volume_t2_cm3: float

    volume_change_t0_t1: float | None
    volume_change_t1_t2: float | None

    trajectory_t0_t1: TrajectoryResponse
    trajectory_t1_t2: TrajectoryResponse

    diffusion: float
    proliferation: float

    calibration_dice: float
    calibration_volume_error: float
    calibration_loss: float

    calibration_identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool

    twin_dice: float
    twin_volume_error: float
    twin_hd95_mm: float | None
    twin_centroid_distance_mm: float | None

    persistence_dice: float
    persistence_volume_error: float

    volume_baseline_dice: float
    volume_baseline_volume_error: float

    twin_minus_persistence_dice: float
    twin_minus_volume_baseline_dice: float

    qc_warning_codes: list[str]

    observed_outside_brain_fraction: float | None
    twin_outside_brain_fraction: float | None

    observed_component_count: int
    twin_component_count: int

    observed_largest_component_fraction: float | None
    twin_largest_component_fraction: float | None


class TwinCohortAnalysisResponse(BaseModel):
    schema_version: int
    kind: str
    sealed: bool

    source_evaluation_sha256: str
    source_freeze_manifest_sha256: str
    analysis_config_sha256: str

    dataset: TwinDatasetResponse
    repository: TwinRepositoryResponse

    analysis_config: TwinAnalysisConfigResponse
    summary: TwinCohortErrorSummaryResponse
    patients: list[TwinCohortPatientErrorResponse]
