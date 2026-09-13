import numpy as np
import pytest

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    explicit_stability_limit,
    reaction_diffusion_step,
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    TreatmentWindow,
)


def test_treatment_reduces_concentration() -> None:
    field = np.full(
        (5, 5, 5),
        0.5,
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=10.0,
        kill_rate=0.1,
    )

    result = reaction_diffusion_step(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        dt=1.0,
        treatment=treatment,
        time_day=0.0,
    )

    assert np.allclose(
        result,
        0.45,
    )


def test_treatment_does_not_act_before_start() -> None:
    field = np.full(
        (5, 5, 5),
        0.5,
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=20.0,
        kill_rate=0.1,
    )

    result = reaction_diffusion_step(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        dt=1.0,
        treatment=treatment,
        time_day=5.0,
    )

    assert np.allclose(
        result,
        field,
    )


def test_treatment_does_not_act_after_end() -> None:
    field = np.full(
        (5, 5, 5),
        0.5,
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=20.0,
        kill_rate=0.1,
    )

    result = reaction_diffusion_step(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        dt=1.0,
        treatment=treatment,
        time_day=20.0,
    )

    assert np.allclose(
        result,
        field,
    )


def test_simulation_splits_step_at_treatment_start() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=1.0,
        end_day=10.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=2.0,
        dt=2.0,
        treatment=treatment,
    )

    assert np.allclose(
        result,
        0.9,
    )


def test_simulation_splits_step_at_treatment_end() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=1.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=2.0,
        dt=2.0,
        treatment=treatment,
    )

    assert np.allclose(
        result,
        0.9,
    )


def test_start_time_day_uses_absolute_treatment_time() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=20.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=1.0,
        dt=1.0,
        treatment=treatment,
        start_time_day=12.0,
    )

    assert np.allclose(
        result,
        0.9,
    )


def test_treatment_contributes_to_stability_limit() -> None:
    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    limit = explicit_stability_limit(
        params,
        spacing=(1.0, 1.0, 1.0),
        kill_rate=0.2,
    )

    assert limit == pytest.approx(
        5.0
    )


def test_unstable_treatment_step_is_rejected() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=100.0,
        kill_rate=0.2,
    )

    with pytest.raises(
        ValueError,
        match="stability limit",
    ):
        reaction_diffusion_step(
            field,
            params,
            spacing=(1.0, 1.0, 1.0),
            dt=6.0,
            treatment=treatment,
            time_day=0.0,
        )


def test_zero_duration_with_treatment_returns_initial_field() -> None:
    field = np.full(
        (3, 3, 3),
        0.5,
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=10.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=0.0,
        dt=1.0,
        treatment=treatment,
    )

    assert np.array_equal(
        result,
        field,
    )