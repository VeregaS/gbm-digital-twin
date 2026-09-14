import numpy as np

from gbm_twin.models.pirt import (
    apply_pirt_fraction,
)
from gbm_twin.models.pirt_solver import (
    simulate_reaction_diffusion_pirt,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)


def zero_dynamics() -> ReactionDiffusionParameters:
    return ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )


def test_single_pirt_fraction_with_zero_dynamics() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    result = simulate_reaction_diffusion_pirt(
        initial,
        zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
        domain_mask=domain,
        fraction_days=(1.0,),
        survival_fraction=0.8,
    )

    expected = apply_pirt_fraction(
        initial,
        survival_fraction=0.8,
        domain_mask=domain,
    )

    np.testing.assert_allclose(
        result,
        expected,
    )


def test_two_pirt_fractions_match_repeated_updates() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    result = simulate_reaction_diffusion_pirt(
        initial,
        zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=3.0,
        dt=1.0,
        domain_mask=domain,
        fraction_days=(
            1.0,
            2.0,
        ),
        survival_fraction=0.8,
    )

    expected = apply_pirt_fraction(
        initial,
        survival_fraction=0.8,
        domain_mask=domain,
    )

    expected = apply_pirt_fraction(
        expected,
        survival_fraction=0.8,
        domain_mask=domain,
    )

    np.testing.assert_allclose(
        result,
        expected,
    )


def test_fraction_at_start_is_applied() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    result = simulate_reaction_diffusion_pirt(
        initial,
        zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=1.0,
        domain_mask=domain,
        fraction_days=(10.0,),
        survival_fraction=0.8,
        start_time_day=10.0,
    )

    expected = apply_pirt_fraction(
        initial,
        survival_fraction=0.8,
        domain_mask=domain,
    )

    np.testing.assert_allclose(
        result,
        expected,
    )


def test_fraction_outside_window_is_ignored() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    parameters = ReactionDiffusionParameters(
        diffusion=0.005,
        proliferation=0.02,
    )

    pirt = simulate_reaction_diffusion_pirt(
        initial,
        parameters,
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
        domain_mask=domain,
        fraction_days=(10.0,),
        survival_fraction=0.8,
    )

    untreated = simulate_reaction_diffusion(
        initial,
        parameters,
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
        domain_mask=domain,
        treatment=None,
    )

    np.testing.assert_allclose(
        pirt,
        untreated,
    )


def test_pirt_solver_preserves_float32() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float32,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    result = simulate_reaction_diffusion_pirt(
        initial,
        zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
        domain_mask=domain,
        fraction_days=(1.0,),
        survival_fraction=0.8,
    )

    assert result.dtype == np.float32


def test_saturated_tumor_is_not_destroyed_by_pirt() -> None:
    initial = np.ones(
        (5, 5, 5),
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    result = simulate_reaction_diffusion_pirt(
        initial,
        zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=31.0,
        dt=1.0,
        domain_mask=domain,
        fraction_days=tuple(
            float(day)
            for day in range(
                1,
                31,
            )
        ),
        survival_fraction=0.786628,
    )

    np.testing.assert_allclose(
        result,
        initial,
    )