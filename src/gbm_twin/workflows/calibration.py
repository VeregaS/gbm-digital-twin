from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gbm_twin.calibration.grid_search import (
    CalibrationResult,
    grid_search,
)
from gbm_twin.data.nifti import same_geometry
from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.models.reaction_diffusion import (
    build_computational_domain,
)
from gbm_twin.models.treatment import (
    PIRTFractionatedRadiotherapy,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)

V2_EFFECTIVE_ALPHA_PER_GY = 0.01
V2_ALPHA_BETA_RATIO_GY = 10.0

V2_LATENT_WIDTH_MM = 4.0
V2_OBSERVATION_THRESHOLD = 0.5
V2_SOFT_TEMPERATURE = 0.05


@dataclass(frozen=True)
class V2CalibrationConfig:
    diffusion_values: tuple[float, ...]
    proliferation_values: tuple[float, ...]

    dt_days: float = 2.0

    latent_width_mm: float = (
        V2_LATENT_WIDTH_MM
    )

    observation_threshold: float = (
        V2_OBSERVATION_THRESHOLD
    )

    soft_temperature: float = (
        V2_SOFT_TEMPERATURE
    )

    volume_weight: float = 0.5

    def __post_init__(self) -> None:
        if not self.diffusion_values:
            raise ValueError(
                "diffusion_values cannot be empty"
            )

        if not self.proliferation_values:
            raise ValueError(
                "proliferation_values cannot be empty"
            )

        if any(
            value < 0
            for value in self.diffusion_values
        ):
            raise ValueError(
                "diffusion values must be "
                "non-negative"
            )

        if any(
            value < 0
            for value
            in self.proliferation_values
        ):
            raise ValueError(
                "proliferation values must be "
                "non-negative"
            )

        if self.dt_days <= 0:
            raise ValueError(
                "dt_days must be positive"
            )

        if self.latent_width_mm <= 0:
            raise ValueError(
                "latent_width_mm must be positive"
            )

        if not (
            0.0
            < self.observation_threshold
            < 1.0
        ):
            raise ValueError(
                "observation_threshold must "
                "be between 0 and 1"
            )

        if self.soft_temperature <= 0:
            raise ValueError(
                "soft_temperature must be positive"
            )

        if self.volume_weight < 0:
            raise ValueError(
                "volume_weight must be "
                "non-negative"
            )


@dataclass(frozen=True)
class V2CalibrationRun:
    patient_id: int

    start_timepoint: str
    observed_timepoint: str

    start_day: float
    observed_day: float
    duration_days: float

    best: CalibrationResult
    candidates: tuple[
        CalibrationResult,
        ...,
    ]


def _validate_interval(
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
) -> float:
    if start.patient_id != observed.patient_id:
        raise ValueError(
            "Calibration timepoints belong "
            "to different patients"
        )

    if not same_geometry(
        start.gtv,
        observed.gtv,
    ):
        raise ValueError(
            f"Patient {start.patient_id}: "
            "calibration timepoint grids "
            "do not match"
        )

    duration_days = (
        observed.days_from_baseline
        - start.days_from_baseline
    )

    if duration_days <= 0:
        raise ValueError(
            "Observed timepoint must occur "
            "after start timepoint"
        )

    return duration_days


def calibrate_v2_interval(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    treatment: (
        PIRTFractionatedRadiotherapy
        | None
    ),
    config: V2CalibrationConfig,
    cache_dir: Path,
    workers: int = 1,
) -> V2CalibrationRun:
    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    duration_days = _validate_interval(
        start,
        observed,
    )

    domain = build_computational_domain(
        start.brain_mask.data,
        start.gtv.data,
    )

    initial = latent_state_from_gtv(
        start.gtv.data,
        start.brain_mask.data,
        spacing=start.spacing,
        parameters=LatentStateParameters(
            transition_width_mm=(
                config.latent_width_mm
            ),
        ),
    )

    observed_mask = (
        observed.gtv.data
        > config.observation_threshold
    )

    results = grid_search(
        initial,
        observed_mask,
        domain,
        spacing=start.spacing,
        duration_days=duration_days,
        dt=config.dt_days,
        diffusion_values=list(
            config.diffusion_values
        ),
        proliferation_values=list(
            config.proliferation_values
        ),
        threshold=(
            config.observation_threshold
        ),
        volume_weight=config.volume_weight,
        treatment=treatment,
        start_time_day=(
            start.days_from_baseline
        ),
        cache_dir=cache_dir,
        workers=workers,
        objective="soft",
        soft_temperature=(
            config.soft_temperature
        ),
    )

    if not results:
        raise RuntimeError(
            "Calibration returned no candidates"
        )

    return V2CalibrationRun(
        patient_id=start.patient_id,
        start_timepoint=start.name,
        observed_timepoint=observed.name,
        start_day=(
            start.days_from_baseline
        ),
        observed_day=(
            observed.days_from_baseline
        ),
        duration_days=duration_days,
        best=results[0],
        candidates=tuple(results),
    )