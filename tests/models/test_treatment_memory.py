from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.treatment_memory import (
    FractionResponseEvent,
    TreatmentMemoryState,
    apply_fraction_response,
    assimilate_observed_density,
    initial_treatment_memory_state,
    simulate_with_treatment_memory,
)


def test_fraction_updates_density_and_persistent_proliferation() -> None:
    state = initial_treatment_memory_state(
        np.full((2, 2, 2), 0.5, dtype=np.float32)
    )

    updated = apply_fraction_response(
        state,
        FractionResponseEvent(
            day=0.0,
            immediate_survival=0.5,
            proliferation_survival=0.9,
        ),
    )

    assert np.allclose(updated.field, 0.375)
    assert np.allclose(updated.proliferation_modifier, 0.9)


def test_assimilation_preserves_treatment_memory() -> None:
    state = TreatmentMemoryState(
        field=np.full((2, 2, 2), 0.4, dtype=np.float32),
        proliferation_modifier=np.full(
            (2, 2, 2),
            0.6,
            dtype=np.float32,
        ),
    )

    assimilated = assimilate_observed_density(
        state,
        np.full((2, 2, 2), 0.2, dtype=np.float32),
    )

    assert np.allclose(assimilated.field, 0.2)
    assert np.allclose(assimilated.proliferation_modifier, 0.6)


def test_persistent_modifier_reduces_future_growth() -> None:
    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.1,
    )
    field = np.full((2, 2, 2), 0.2, dtype=np.float32)

    full_growth = TreatmentMemoryState(
        field=field.copy(),
        proliferation_modifier=np.ones_like(field),
    )
    suppressed_growth = TreatmentMemoryState(
        field=field.copy(),
        proliferation_modifier=np.full_like(field, 0.5),
    )

    full_result = simulate_with_treatment_memory(
        full_growth,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=0.5,
    )
    suppressed_result = simulate_with_treatment_memory(
        suppressed_growth,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=0.5,
    )

    assert np.all(suppressed_result.field < full_result.field)


def test_simulator_applies_fraction_at_interval_start() -> None:
    state = initial_treatment_memory_state(
        np.full((2, 2, 2), 0.5, dtype=np.float32)
    )
    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    result = simulate_with_treatment_memory(
        state,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=1.0,
        dt=0.5,
        fraction_events=(
            FractionResponseEvent(
                day=0.0,
                immediate_survival=0.5,
                proliferation_survival=0.8,
            ),
        ),
    )

    assert np.allclose(result.field, 0.375)
    assert np.allclose(result.proliferation_modifier, 0.8)


def test_fraction_outside_interval_is_rejected() -> None:
    state = initial_treatment_memory_state(
        np.full((2, 2, 2), 0.5, dtype=np.float32)
    )

    with pytest.raises(ValueError, match="outside"):
        simulate_with_treatment_memory(
            state,
            ReactionDiffusionParameters(
                diffusion=0.0,
                proliferation=0.0,
            ),
            spacing=(1.0, 1.0, 1.0),
            duration_days=1.0,
            dt=0.5,
            fraction_events=(
                FractionResponseEvent(
                    day=2.0,
                    immediate_survival=1.0,
                ),
            ),
        )
