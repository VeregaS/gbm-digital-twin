import math

import numpy as np
import pytest

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
)


def zero_dynamics_parameters() -> ReactionDiffusionParameters:
    return ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )


def test_post_rt_effect_is_zero_before_start() -> None:
    effect = PostRadiotherapyEffect(
        start_day=10.0,
        initial_kill_rate=0.1,
        decay_time_days=20.0,
    )

    assert (
        effect.kill_rate_at(5.0)
        == 0.0
    )


def test_post_rt_effect_starts_at_initial_rate() -> None:
    effect = PostRadiotherapyEffect(
        start_day=10.0,
        initial_kill_rate=0.1,
        decay_time_days=20.0,
    )

    assert (
        effect.kill_rate_at(10.0)
        == pytest.approx(0.1)
    )


def test_post_rt_effect_decays_exponentially() -> None:
    effect = PostRadiotherapyEffect(
        start_day=10.0,
        initial_kill_rate=0.1,
        decay_time_days=20.0,
    )

    assert (
        effect.kill_rate_at(30.0)
        == pytest.approx(
            0.1 / math.e
        )
    )


def test_post_rt_effect_rejects_negative_start() -> None:
    with pytest.raises(
        ValueError,
        match="start day",
    ):
        PostRadiotherapyEffect(
            start_day=-1.0,
            initial_kill_rate=0.1,
            decay_time_days=20.0,
        )


def test_post_rt_effect_rejects_negative_kill_rate() -> None:
    with pytest.raises(
        ValueError,
        match="kill rate",
    ):
        PostRadiotherapyEffect(
            start_day=10.0,
            initial_kill_rate=-0.1,
            decay_time_days=20.0,
        )


def test_post_rt_effect_rejects_nonpositive_decay_time() -> None:
    with pytest.raises(
        ValueError,
        match="Decay time",
    ):
        PostRadiotherapyEffect(
            start_day=10.0,
            initial_kill_rate=0.1,
            decay_time_days=0.0,
        )


def test_protocol_rejects_post_effect_before_last_fraction() -> None:
    fractions = FractionatedRadiotherapy(
        fraction_days=(
            10.0,
            11.0,
            12.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.01,
    )

    effect = PostRadiotherapyEffect(
        start_day=11.0,
        initial_kill_rate=0.1,
        decay_time_days=20.0,
    )

    with pytest.raises(
        ValueError,
        match="last RT fraction",
    ):
        RadiotherapyProtocol(
            fractions=fractions,
            post_effect=effect,
        )


def test_solver_applies_post_rt_effect_after_fraction() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    alpha = (
        math.log(2.0)
        / 2.0
    )

    fractions = FractionatedRadiotherapy(
        fraction_days=(1.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=alpha,
        beta_per_gy2=0.0,
    )

    effect = PostRadiotherapyEffect(
        start_day=1.0,
        initial_kill_rate=0.1,
        decay_time_days=100.0,
    )

    protocol = RadiotherapyProtocol(
        fractions=fractions,
        post_effect=effect,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=2.0,
        dt=1.0,
        treatment=protocol,
    )

    assert np.allclose(
        result,
        0.45,
    )


def test_solver_splits_step_at_post_rt_start() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    effect = PostRadiotherapyEffect(
        start_day=1.0,
        initial_kill_rate=0.1,
        decay_time_days=100.0,
    )

    result = simulate_reaction_diffusion(
        field,
        zero_dynamics_parameters(),
        spacing=(1.0, 1.0, 1.0),
        duration_days=2.0,
        dt=2.0,
        treatment=effect,
    )

    assert np.allclose(
        result,
        0.9,
    )


def test_post_rt_effect_can_drive_regression() -> None:
    field = np.full(
        (3, 3, 3),
        0.5,
        dtype=float,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.03,
    )

    effect = PostRadiotherapyEffect(
        start_day=0.0,
        initial_kill_rate=0.1,
        decay_time_days=30.0,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=5.0,
        dt=0.5,
        treatment=effect,
    )

    assert np.all(
        result < field
    )