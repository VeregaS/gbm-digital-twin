from __future__ import annotations

import numpy as np

from gbm_twin.models.delayed_response import (
    DelayedResponseEvent,
    DelayedResponseParameters,
    assimilate_visible_density,
    initial_delayed_response_state,
    simulate_delayed_response,
    visible_density,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.treatment_memory import (
    FractionResponseEvent,
    initial_treatment_memory_state,
    simulate_with_treatment_memory,
)


def test_zero_damage_transfer_matches_stage8_state_dynamics() -> None:
    field = np.zeros((7, 7, 7), dtype=np.float32)
    field[3, 3, 3] = 0.8
    domain = np.ones_like(field, dtype=bool)
    growth = ReactionDiffusionParameters(
        diffusion=0.01,
        proliferation=0.02,
    )

    stage8 = simulate_with_treatment_memory(
        initial_treatment_memory_state(
            field,
            domain_mask=domain,
        ),
        growth,
        spacing=(2.0, 2.0, 2.0),
        duration_days=4.0,
        dt=1.0,
        start_time_day=0.0,
        fraction_events=(
            FractionResponseEvent(
                day=1.0,
                immediate_survival=0.85,
                proliferation_survival=0.98,
            ),
        ),
        domain_mask=domain,
    )
    stage9 = simulate_delayed_response(
        initial_delayed_response_state(
            field,
            domain_mask=domain,
        ),
        growth,
        delayed=DelayedResponseParameters(
            damage_transfer_fraction=0.0,
            damage_half_life_days=30.0,
            damaged_visibility=1.0,
        ),
        spacing=(2.0, 2.0, 2.0),
        duration_days=4.0,
        dt=1.0,
        start_time_day=0.0,
        events=(
            DelayedResponseEvent(
                day=1.0,
                immediate_survival=0.85,
                proliferation_survival=0.98,
            ),
        ),
        domain_mask=domain,
    )

    np.testing.assert_allclose(
        stage9.viable,
        stage8.field,
        rtol=0.0,
        atol=1e-7,
    )
    np.testing.assert_allclose(
        stage9.proliferation_modifier,
        stage8.proliferation_modifier,
        rtol=0.0,
        atol=1e-7,
    )
    assert not np.any(stage9.damaged)


def test_damaged_compartment_produces_delayed_visible_regression() -> None:
    field = np.zeros((3, 3, 3), dtype=np.float32)
    field[1, 1, 1] = 0.5
    growth = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )
    delayed = DelayedResponseParameters(
        damage_transfer_fraction=1.0,
        damage_half_life_days=10.0,
        damaged_visibility=1.0,
    )
    initial = initial_delayed_response_state(field)

    after_fraction = simulate_delayed_response(
        initial,
        growth,
        delayed=delayed,
        spacing=(2.0, 2.0, 2.0),
        duration_days=0.0,
        dt=1.0,
        events=(
            DelayedResponseEvent(
                day=0.0,
                immediate_survival=0.0,
            ),
        ),
    )
    later = simulate_delayed_response(
        after_fraction,
        growth,
        delayed=delayed,
        spacing=(2.0, 2.0, 2.0),
        duration_days=10.0,
        dt=1.0,
        start_time_day=0.0,
    )

    immediate_visible = float(visible_density(after_fraction, delayed)[1, 1, 1])
    later_visible = float(visible_density(later, delayed)[1, 1, 1])

    assert immediate_visible == 0.5
    assert later_visible < immediate_visible
    assert float(later.damaged[1, 1, 1]) < float(
        after_fraction.damaged[1, 1, 1]
    )


def test_assimilation_retains_only_mri_compatible_damaged_burden() -> None:
    field = np.zeros((3, 3, 3), dtype=np.float32)
    field[1, 1, 1] = 0.6
    state = initial_delayed_response_state(field)
    state = type(state)(
        viable=np.zeros_like(field),
        damaged=np.full_like(field, 0.6),
        proliferation_modifier=np.ones_like(field),
    )
    observed = np.full_like(field, 0.3)
    parameters = DelayedResponseParameters(
        damage_transfer_fraction=1.0,
        damage_half_life_days=30.0,
        damaged_visibility=0.5,
    )

    assimilated = assimilate_visible_density(
        state,
        observed,
        parameters=parameters,
    )

    np.testing.assert_allclose(
        visible_density(assimilated, parameters),
        observed,
        rtol=0.0,
        atol=1e-7,
    )
    assert np.all(assimilated.damaged <= 0.6)
