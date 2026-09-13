import math

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
    FractionatedRadiotherapy,
    TreatmentWindow,
)


def zero_dynamics_parameters() -> ReactionDiffusionParameters:
    return ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )


def test_treatment_reduces_concentration() -> None:
    field = np.full(
        (5, 5, 5),
        0.5,
        dtype=float,
    )

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=10.0,
        kill_rate=0.1,
    )

    result = reaction_diffusion_step(
        field,
        zero_dynamics_parameters(),
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

    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=20.0,
        kill_rate=0.1,
    )

    result = reaction_diffusion_step(
        field,
        zero_dynamics_parameters(),
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

    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=20.0,
        kill_rate=0.1,
    )

    result = reaction_diffusion_step(
        field,
        zero_dynamics_parameters(),
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

    treatment = TreatmentWindow(
        start_day=1.0,
        end_day=10.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
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

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=1.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
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

    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=20.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
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
    limit = explicit_stability_limit(
        zero_dynamics_parameters(),
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
            zero_dynamics_parameters(),
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

    treatment = TreatmentWindow(
        start_day=0.0,
        end_day=10.0,
        kill_rate=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=0.0,
        dt=1.0,
        treatment=treatment,
    )

    assert np.array_equal(
        result,
        field,
    )


def test_single_fraction_reduces_concentration() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(1.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=2.0,
        dt=2.0,
        treatment=treatment,
    )

    expected_survival = math.exp(
        -(
            0.1 * 2.0
            + 0.02 * 2.0**2
        )
    )

    assert np.allclose(
        result,
        expected_survival,
    )


def test_fraction_inside_large_step_is_applied() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(1.5,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=3.0,
        dt=3.0,
        treatment=treatment,
    )

    assert np.allclose(
        result,
        treatment.survival_fraction_per_fraction,
    )


def test_multiple_fractions_are_applied_once_each() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(
            1.0,
            2.0,
            3.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=4.0,
        dt=4.0,
        treatment=treatment,
    )

    expected = (
        treatment.survival_fraction_per_fraction
        ** 3
    )

    assert np.allclose(
        result,
        expected,
    )


def test_fraction_at_simulation_start_is_applied() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(10.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=1.0,
        dt=1.0,
        treatment=treatment,
        start_time_day=10.0,
    )

    assert np.allclose(
        result,
        treatment.survival_fraction_per_fraction,
    )


def test_fraction_at_simulation_end_is_applied() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(2.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=2.0,
        dt=2.0,
        treatment=treatment,
    )

    assert np.allclose(
        result,
        treatment.survival_fraction_per_fraction,
    )


def test_fraction_before_simulation_interval_is_not_applied() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(5.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=5.0,
        dt=2.0,
        treatment=treatment,
        start_time_day=10.0,
    )

    assert np.array_equal(
        result,
        field,
    )


def test_zero_duration_does_not_apply_fraction() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(0.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=0.0,
        dt=1.0,
        treatment=treatment,
    )

    assert np.array_equal(
        result,
        field,
    )