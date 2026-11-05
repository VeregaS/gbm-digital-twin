from __future__ import annotations

import numpy as np

from gbm_twin.models.decoupled_damage import (
    DecoupledDamageEvent,
    DecoupledDamageParameters,
    initial_decoupled_damage_state,
    simulate_decoupled_damage,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters


def test_stage10_state_retains_cleared_damage_as_occupancy(
) -> None:
    field = np.zeros(
        (
            5,
            5,
            5,
        ),
        dtype=np.float32,
    )

    field[
        2,
        2,
        2,
    ] = 0.5

    state = (
        initial_decoupled_damage_state(
            field
        )
    )

    after_rt = (
        simulate_decoupled_damage(
            state,
            ReactionDiffusionParameters(
                diffusion=0.0,
                proliferation=0.0,
            ),
            parameters=(
                DecoupledDamageParameters(
                    damage_half_life_days=10.0,
                )
            ),
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            duration_days=0.0,
            dt=1.0,
            events=(
                DecoupledDamageEvent(
                    day=0.0,
                    immediate_survival=0.0,
                ),
            ),
        )
    )

    later = (
        simulate_decoupled_damage(
            after_rt,
            ReactionDiffusionParameters(
                diffusion=0.0,
                proliferation=0.0,
            ),
            parameters=(
                DecoupledDamageParameters(
                    damage_half_life_days=10.0,
                )
            ),
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            duration_days=10.0,
            dt=1.0,
        )
    )

    before_occupancy = (
        after_rt.damaged
        + after_rt.inert
    )

    after_occupancy = (
        later.damaged
        + later.inert
    )

    np.testing.assert_allclose(
        after_occupancy,
        before_occupancy,
        rtol=0.0,
        atol=1e-6,
    )
