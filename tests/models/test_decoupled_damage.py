from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.models.decoupled_damage import (
    DecoupledDamageEvent,
    DecoupledDamageParameters,
    DecoupledDamageState,
    assimilate_visible_density,
    simulate_decoupled_damage,
    visible_density,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters


def _single_voxel_state(
    *,
    viable: float,
    damaged: float,
    inert: float,
    modifier: float = 1.0,
) -> DecoupledDamageState:
    shape = (
        3,
        3,
        3,
    )

    v = np.zeros(
        shape,
        dtype=np.float32,
    )

    d = np.zeros_like(
        v
    )

    q = np.zeros_like(
        v
    )

    m = np.ones_like(
        v
    )

    v[
        1,
        1,
        1,
    ] = viable

    d[
        1,
        1,
        1,
    ] = damaged

    q[
        1,
        1,
        1,
    ] = inert

    m[
        1,
        1,
        1,
    ] = modifier

    return DecoupledDamageState(
        viable=v,
        damaged=d,
        inert=q,
        proliferation_modifier=m,
    )


def test_visible_clearance_transfers_to_inert_occupancy(
) -> None:
    state = _single_voxel_state(
        viable=0.0,
        damaged=0.4,
        inert=0.1,
    )

    result = (
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
            duration_days=10.0,
            dt=1.0,
        )
    )

    assert float(
        result.damaged[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.2,
        abs=1e-6,
    )

    assert float(
        result.inert[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.3,
        abs=1e-6,
    )

    assert float(
        visible_density(
            result
        )[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.2,
        abs=1e-6,
    )

    assert float(
        (
            result.damaged
            + result.inert
        )[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.5,
        abs=1e-6,
    )


def test_assimilation_preserves_compatible_damaged_and_inert_states(
) -> None:
    state = _single_voxel_state(
        viable=0.1,
        damaged=0.3,
        inert=0.2,
        modifier=0.7,
    )

    observed = np.zeros(
        (
            3,
            3,
            3,
        ),
        dtype=np.float32,
    )

    observed[
        1,
        1,
        1,
    ] = 0.5

    result = (
        assimilate_visible_density(
            state,
            observed,
        )
    )

    assert float(
        result.damaged[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.3
    )

    assert float(
        result.inert[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.2
    )

    assert float(
        result.viable[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.2
    )

    assert float(
        result.proliferation_modifier[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.7
    )


def test_assimilation_caps_damaged_state_to_visible_observation(
) -> None:
    state = _single_voxel_state(
        viable=0.0,
        damaged=0.6,
        inert=0.2,
    )

    observed = np.zeros(
        (
            3,
            3,
            3,
        ),
        dtype=np.float32,
    )

    observed[
        1,
        1,
        1,
    ] = 0.3

    result = (
        assimilate_visible_density(
            state,
            observed,
        )
    )

    assert float(
        result.damaged[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.3
    )

    assert float(
        result.viable[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.0
    )


def test_assimilation_reduces_only_incompatible_inert_occupancy(
) -> None:
    state = _single_voxel_state(
        viable=0.1,
        damaged=0.2,
        inert=0.4,
    )

    observed = np.zeros(
        (
            3,
            3,
            3,
        ),
        dtype=np.float32,
    )

    observed[
        1,
        1,
        1,
    ] = 0.8

    result = (
        assimilate_visible_density(
            state,
            observed,
        )
    )

    assert float(
        result.inert[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.2,
        abs=1e-6,
    )

    assert float(
        result.damaged[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.2
    )

    assert float(
        result.viable[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.6,
        abs=1e-6,
    )


def test_fraction_preserves_total_occupancy_and_builds_damaged_state(
) -> None:
    state = _single_voxel_state(
        viable=0.5,
        damaged=0.0,
        inert=0.2,
    )

    result = (
        simulate_decoupled_damage(
            state,
            ReactionDiffusionParameters(
                diffusion=0.0,
                proliferation=0.0,
            ),
            parameters=(
                DecoupledDamageParameters(
                    damage_half_life_days=1000.0,
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
                    proliferation_survival=0.9,
                ),
            ),
        )
    )

    total_before = (
        state.viable
        + state.damaged
        + state.inert
    )

    total_after = (
        result.viable
        + result.damaged
        + result.inert
    )

    np.testing.assert_allclose(
        total_after,
        total_before,
        rtol=0.0,
        atol=1e-7,
    )

    assert float(
        result.damaged[
            1,
            1,
            1,
        ]
    ) > 0.0

    assert float(
        result.proliferation_modifier[
            1,
            1,
            1,
        ]
    ) == pytest.approx(
        0.9
    )
