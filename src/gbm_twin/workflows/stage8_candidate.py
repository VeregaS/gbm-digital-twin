from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.calibration.stage8 import (
    Stage8CalibrationConfig,
    calibrate_stage8_interval,
)
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.treatment_memory import FractionResponseEvent
from gbm_twin.workflows.stage8_forecast import simulate_stage8_forecast
from gbm_twin.workflows.stage8_model_family import Stage8ModelCandidate
from gbm_twin.workflows.stage8_patient import (
    Stage8EvaluationTarget,
    Stage8ForecastInputs,
)
from gbm_twin.workflows.stage8_treatment import build_stage8_radiotherapy_events


@dataclass(frozen=True)
class Stage8PatientCandidateEvaluation:
    patient_id: int
    candidate_id: str
    use_spatial_rtdose: bool
    effective_alpha_per_gy: float
    alpha_beta_ratio_gy: float
    proliferation_survival: float
    diffusion: float
    proliferation: float
    calibration_dice: float
    calibration_volume_error: float
    calibration_loss: float
    calibration_identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool
    t2_dice: float
    t2_relative_volume_error: float
    t2_hd95_mm: float | None
    t2_centroid_distance_mm: float | None


def _events_for_interval(
    events: tuple[FractionResponseEvent, ...],
    *,
    start_day: float,
    end_day: float,
) -> tuple[FractionResponseEvent, ...]:
    tolerance = 1e-9
    return tuple(
        event
        for event in events
        if event.day >= start_day - tolerance
        and event.day <= end_day + tolerance
    )


def evaluate_stage8_candidate(
    *,
    inputs: Stage8ForecastInputs,
    target: Stage8EvaluationTarget,
    candidate: Stage8ModelCandidate,
    observation_parameters: MRIDetectionObservationParameters,
    calibration_config: Stage8CalibrationConfig,
    cache_root: Path,
    workers: int,
    progress: Callable[[str], None] | None = None,
) -> Stage8PatientCandidateEvaluation:
    if target.patient_id != inputs.patient_id:
        raise ValueError("Stage 8 target does not match prepared patient inputs")

    cumulative_rtdose: np.ndarray | None = None
    if candidate.use_spatial_rtdose:
        if inputs.cumulative_rtdose is None:
            raise FileNotFoundError(
                f"Patient {inputs.patient_id}: spatial candidate requires local RTDOSE"
            )
        cumulative_rtdose = inputs.cumulative_rtdose

    radiobiology = RadiobiologyParameters(
        alpha_per_gy=candidate.effective_alpha_per_gy,
        alpha_beta_ratio_gy=candidate.alpha_beta_ratio_gy,
    )
    rt_events = build_stage8_radiotherapy_events(
        inputs.schedule,
        radiobiology,
        proliferation_survival=candidate.proliferation_survival,
        cumulative_rtdose=cumulative_rtdose,
    )
    calibration = calibrate_stage8_interval(
        initial_state=inputs.initial_state,
        observed_mask=inputs.observed.gtv.data > 0.5,
        domain_mask=inputs.domain_mask,
        spacing=inputs.start.spacing,
        duration_days=(
            inputs.observed.days_from_baseline
            - inputs.start.days_from_baseline
        ),
        start_time_day=inputs.start.days_from_baseline,
        fraction_events=_events_for_interval(
            rt_events.events,
            start_day=inputs.start.days_from_baseline,
            end_day=inputs.observed.days_from_baseline,
        ),
        config=calibration_config,
        cache_dir=(
            cache_root
            / f"patient-{inputs.patient_id}"
            / candidate.candidate_id
        ),
        workers=workers,
        progress=progress,
    )
    forecast = simulate_stage8_forecast(
        start=inputs.start,
        observed=inputs.observed,
        target_day=target.target.days_from_baseline,
        parameters=ReactionDiffusionParameters(
            diffusion=calibration.best.diffusion,
            proliferation=calibration.best.proliferation,
        ),
        schedule=inputs.schedule,
        radiobiology=radiobiology,
        proliferation_survival=candidate.proliferation_survival,
        dt_days=calibration_config.dt_days,
        observation_parameters=observation_parameters,
        cumulative_rtdose=cumulative_rtdose,
    )
    observed_t2 = np.asarray(target.target.gtv.data > 0.5, dtype=bool)
    predicted_t2 = forecast.prediction_mask

    return Stage8PatientCandidateEvaluation(
        patient_id=inputs.patient_id,
        candidate_id=candidate.candidate_id,
        use_spatial_rtdose=candidate.use_spatial_rtdose,
        effective_alpha_per_gy=candidate.effective_alpha_per_gy,
        alpha_beta_ratio_gy=candidate.alpha_beta_ratio_gy,
        proliferation_survival=candidate.proliferation_survival,
        diffusion=calibration.best.diffusion,
        proliferation=calibration.best.proliferation,
        calibration_dice=calibration.best.dice,
        calibration_volume_error=calibration.best.volume_error,
        calibration_loss=calibration.best.loss,
        calibration_identifiable=calibration.diagnostics.identifiable,
        diffusion_at_boundary=(
            calibration.diagnostics.diffusion_at_boundary
        ),
        proliferation_at_boundary=(
            calibration.diagnostics.proliferation_at_boundary
        ),
        t2_dice=dice_score(predicted_t2, observed_t2),
        t2_relative_volume_error=relative_volume_error(
            predicted_t2,
            observed_t2,
        ),
        t2_hd95_mm=hausdorff95_mm(
            predicted_t2,
            observed_t2,
            spacing=target.target.spacing,
        ),
        t2_centroid_distance_mm=centroid_distance_mm(
            predicted_t2,
            observed_t2,
            spacing=target.target.spacing,
        ),
    )
