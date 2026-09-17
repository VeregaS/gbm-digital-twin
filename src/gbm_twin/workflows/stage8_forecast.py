from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gbm_twin.data.nifti import same_geometry
from gbm_twin.models.observation import (
    MRIDetectionObservationParameters,
    latent_density_from_mri_detection,
)
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.rt_schedule import ReconstructedRadiotherapySchedule
from gbm_twin.models.treatment_memory import (
    TreatmentMemoryState,
    assimilate_observed_density,
    initial_treatment_memory_state,
    simulate_with_treatment_memory,
)
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.stage8_treatment import (
    Stage8RadiotherapyEvents,
    build_stage8_radiotherapy_events,
)


@dataclass(frozen=True)
class Stage8ForecastResult:
    patient_id: int
    calibrated_to_timepoint: str
    target_day: float
    pre_assimilation_state: TreatmentMemoryState
    assimilated_state: TreatmentMemoryState
    prediction_state: TreatmentMemoryState
    prediction_mask: np.ndarray
    radiotherapy: Stage8RadiotherapyEvents


def _validate_longitudinal_geometry(
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
) -> None:
    if start.patient_id != observed.patient_id:
        raise ValueError("Stage 8 timepoints belong to different patients")

    if not same_geometry(start.gtv, observed.gtv):
        raise ValueError(
            "Stage 8 requires registered t0/t1 GTV on the same geometry"
        )

    if not same_geometry(start.brain_mask, observed.brain_mask):
        raise ValueError(
            "Stage 8 requires registered t0/t1 brain masks on the same geometry"
        )


def _events_for_interval(
    radiotherapy: Stage8RadiotherapyEvents,
    *,
    start_day: float,
    end_day: float,
    include_start: bool,
) -> tuple:
    tolerance = 1e-9

    return tuple(
        event
        for event in radiotherapy.events
        if (
            (
                event.day > start_day + tolerance
                or (
                    include_start
                    and abs(event.day - start_day) <= tolerance
                )
            )
            and event.day <= end_day + tolerance
        )
    )


def simulate_stage8_forecast(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target_day: float,
    parameters: ReactionDiffusionParameters,
    schedule: ReconstructedRadiotherapySchedule,
    radiobiology: RadiobiologyParameters,
    proliferation_survival: float,
    dt_days: float,
    observation_parameters: MRIDetectionObservationParameters,
    cumulative_rtdose: np.ndarray | None = None,
    start_infiltrative_mask: np.ndarray | None = None,
    observed_infiltrative_mask: np.ndarray | None = None,
) -> Stage8ForecastResult:
    """Calibrate state to t1 by assimilation and forecast without loading t2.

    The biological RT-memory state is propagated through t0->t1 and preserved
    across MRI assimilation. The t1 observation updates the tumor-density field
    but does not reset treatment-induced proliferation suppression.
    """

    _validate_longitudinal_geometry(start, observed)

    if observed.days_from_baseline <= start.days_from_baseline:
        raise ValueError("observed timepoint must follow start timepoint")

    if target_day <= observed.days_from_baseline:
        raise ValueError("target_day must follow observed timepoint")

    if dt_days <= 0.0:
        raise ValueError("dt_days must be positive")

    domain = np.asarray(
        (start.brain_mask.data > 0.5)
        | (observed.brain_mask.data > 0.5)
        | (start.gtv.data > 0.5)
        | (observed.gtv.data > 0.5),
        dtype=bool,
    )

    initial_density = latent_density_from_mri_detection(
        start.gtv.data > 0.5,
        domain,
        spacing=start.spacing,
        infiltrative_mask=start_infiltrative_mask,
        parameters=observation_parameters,
    )
    initial_state = initial_treatment_memory_state(
        initial_density,
        domain_mask=domain,
    )

    radiotherapy_events = build_stage8_radiotherapy_events(
        schedule,
        radiobiology,
        proliferation_survival=proliferation_survival,
        cumulative_rtdose=cumulative_rtdose,
    )

    calibration_events = _events_for_interval(
        radiotherapy_events,
        start_day=start.days_from_baseline,
        end_day=observed.days_from_baseline,
        include_start=True,
    )

    pre_assimilation = simulate_with_treatment_memory(
        initial_state,
        parameters,
        spacing=start.spacing,
        duration_days=(
            observed.days_from_baseline - start.days_from_baseline
        ),
        dt=dt_days,
        start_time_day=start.days_from_baseline,
        fraction_events=calibration_events,
        domain_mask=domain,
    )

    observed_density = latent_density_from_mri_detection(
        observed.gtv.data > 0.5,
        domain,
        spacing=observed.spacing,
        infiltrative_mask=observed_infiltrative_mask,
        parameters=observation_parameters,
    )

    assimilated = assimilate_observed_density(
        pre_assimilation,
        observed_density,
        observation_weight=1.0,
        domain_mask=domain,
    )

    forecast_events = _events_for_interval(
        radiotherapy_events,
        start_day=observed.days_from_baseline,
        end_day=target_day,
        include_start=False,
    )

    prediction = simulate_with_treatment_memory(
        assimilated,
        parameters,
        spacing=observed.spacing,
        duration_days=target_day - observed.days_from_baseline,
        dt=dt_days,
        start_time_day=observed.days_from_baseline,
        fraction_events=forecast_events,
        domain_mask=domain,
    )

    prediction_mask = np.asarray(
        prediction.field >= observation_parameters.enhancing_threshold,
        dtype=bool,
    )

    return Stage8ForecastResult(
        patient_id=start.patient_id,
        calibrated_to_timepoint=observed.name,
        target_day=target_day,
        pre_assimilation_state=pre_assimilation,
        assimilated_state=assimilated,
        prediction_state=prediction,
        prediction_mask=prediction_mask,
        radiotherapy=radiotherapy_events,
    )
