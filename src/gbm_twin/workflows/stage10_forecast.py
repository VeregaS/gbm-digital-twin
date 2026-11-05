from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gbm_twin.models.decoupled_damage import (
    DecoupledDamageEvent,
    DecoupledDamageParameters,
    DecoupledDamageState,
    assimilate_visible_density,
    initial_decoupled_damage_state,
    simulate_decoupled_damage,
    visible_density,
)
from gbm_twin.models.observation import (
    MRIDetectionObservationParameters,
    latent_density_from_mri_detection,
)
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.workflows.stage8_patient import Stage8ForecastInputs
from gbm_twin.workflows.stage8_treatment import build_stage8_radiotherapy_events


@dataclass(frozen=True)
class Stage10ForecastResult:
    patient_id: int
    target_day: float
    pre_assimilation_state: DecoupledDamageState
    assimilated_state: DecoupledDamageState
    prediction_state: DecoupledDamageState
    prediction_visible_density: np.ndarray
    prediction_mask: np.ndarray


def _events_for_interval(
    events: tuple[
        DecoupledDamageEvent,
        ...,
    ],
    *,
    start_day: float,
    end_day: float,
    include_start: bool,
) -> tuple[
    DecoupledDamageEvent,
    ...,
]:
    tolerance = 1e-9

    return tuple(
        event
        for event in events
        if (
            (
                event.day
                > start_day
                + tolerance
                or (
                    include_start
                    and abs(
                        event.day
                        - start_day
                    )
                    <= tolerance
                )
            )
            and event.day
            <= end_day
            + tolerance
        )
    )


def simulate_stage10_forecast(
    *,
    inputs: Stage8ForecastInputs,
    target_day: float,
    growth: ReactionDiffusionParameters,
    radiobiology: RadiobiologyParameters,
    proliferation_survival: float,
    damage_half_life_days: float,
    dt_days: float,
    observation_parameters: MRIDetectionObservationParameters,
) -> Stage10ForecastResult:
    """Forecast with decoupled MRI-visible damage and inert occupancy.

    Patient-specific D/rho, radiobiology and Stage 8 proliferation survival
    remain frozen. Stage 10 varies only the global visible-damage half-life.
    """

    start = inputs.start
    observed = inputs.observed

    if (
        target_day
        <= observed.days_from_baseline
    ):
        raise ValueError(
            "target_day must follow observed timepoint"
        )

    if dt_days <= 0.0:
        raise ValueError(
            "dt_days must be positive"
        )

    domain = np.asarray(
        inputs.domain_mask,
        dtype=bool,
    )

    start_density = (
        latent_density_from_mri_detection(
            start.gtv.data > 0.5,
            domain,
            spacing=start.spacing,
            parameters=(
                observation_parameters
            ),
        )
    )

    state = (
        initial_decoupled_damage_state(
            start_density,
            domain_mask=domain,
        )
    )

    rt = (
        build_stage8_radiotherapy_events(
            inputs.schedule,
            radiobiology,
            proliferation_survival=(
                proliferation_survival
            ),
            cumulative_rtdose=(
                inputs.cumulative_rtdose
            ),
        )
    )

    events = tuple(
        DecoupledDamageEvent(
            day=event.day,
            immediate_survival=(
                event.immediate_survival
            ),
            proliferation_survival=(
                event
                .proliferation_survival
            ),
        )
        for event in rt.events
    )

    parameters = (
        DecoupledDamageParameters(
            damage_half_life_days=(
                damage_half_life_days
            ),
        )
    )

    pre_assimilation = (
        simulate_decoupled_damage(
            state,
            growth,
            parameters=parameters,
            spacing=start.spacing,
            duration_days=(
                observed.days_from_baseline
                - start.days_from_baseline
            ),
            dt=dt_days,
            start_time_day=(
                start.days_from_baseline
            ),
            events=_events_for_interval(
                events,
                start_day=(
                    start.days_from_baseline
                ),
                end_day=(
                    observed.days_from_baseline
                ),
                include_start=True,
            ),
            domain_mask=domain,
        )
    )

    observed_density = (
        latent_density_from_mri_detection(
            observed.gtv.data > 0.5,
            domain,
            spacing=observed.spacing,
            parameters=(
                observation_parameters
            ),
        )
    )

    assimilated = (
        assimilate_visible_density(
            pre_assimilation,
            observed_density,
            domain_mask=domain,
        )
    )

    prediction = (
        simulate_decoupled_damage(
            assimilated,
            growth,
            parameters=parameters,
            spacing=observed.spacing,
            duration_days=(
                target_day
                - observed
                .days_from_baseline
            ),
            dt=dt_days,
            start_time_day=(
                observed.days_from_baseline
            ),
            events=_events_for_interval(
                events,
                start_day=(
                    observed.days_from_baseline
                ),
                end_day=target_day,
                include_start=False,
            ),
            domain_mask=domain,
        )
    )

    predicted_density = (
        visible_density(
            prediction
        )
    )

    predicted_mask = np.asarray(
        predicted_density
        >= observation_parameters
        .enhancing_threshold,
        dtype=bool,
    )

    return Stage10ForecastResult(
        patient_id=(
            inputs.patient_id
        ),
        target_day=target_day,
        pre_assimilation_state=(
            pre_assimilation
        ),
        assimilated_state=(
            assimilated
        ),
        prediction_state=(
            prediction
        ),
        prediction_visible_density=(
            predicted_density
        ),
        prediction_mask=(
            predicted_mask
        ),
    )
