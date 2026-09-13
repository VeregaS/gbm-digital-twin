import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    gaussian_initial_condition,
)
from gbm_twin.models.solver import (
    explicit_stability_limit,
    laplacian_3d,
    reaction_diffusion_step,
    simulate_reaction_diffusion,
)


def test_constant_field_has_zero_laplacian() -> None:
    field = np.ones((7, 7, 7), dtype=float)

    result = laplacian_3d(
        field,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.allclose(result, 0.0)


def test_impulse_laplacian_center() -> None:
    field = np.zeros((7, 7, 7), dtype=float)
    field[3, 3, 3] = 1.0

    result = laplacian_3d(
        field,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.isclose(result[3, 3, 3], -6.0)

    assert np.isclose(result[2, 3, 3], 1.0)
    assert np.isclose(result[4, 3, 3], 1.0)
    assert np.isclose(result[3, 2, 3], 1.0)
    assert np.isclose(result[3, 4, 3], 1.0)
    assert np.isclose(result[3, 3, 2], 1.0)
    assert np.isclose(result[3, 3, 4], 1.0)
    
def test_zero_dynamics_preserves_field() -> None:
    rng = np.random.default_rng(42)
    field = rng.random((7, 7, 7))

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )

    result = reaction_diffusion_step(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        dt=1.0,
    )

    assert np.allclose(result, field)


def test_proliferation_only_increases_concentration() -> None:
    field = np.full((5, 5, 5), 0.25)

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.1,
    )

    result = reaction_diffusion_step(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        dt=1.0,
    )

    assert np.all(result > field)


def test_unstable_dt_is_rejected() -> None:
    params = ReactionDiffusionParameters(
        diffusion=1.0,
        proliferation=0.0,
    )

    limit = explicit_stability_limit(
        params,
        (1.0, 1.0, 1.0),
    )

    field = np.zeros((5, 5, 5))

    try:
        reaction_diffusion_step(
            field,
            params,
            spacing=(1.0, 1.0, 1.0),
            dt=limit * 2,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected unstable dt to be rejected")
    
def test_zero_duration_returns_initial_field() -> None:
    field = np.full((5, 5, 5), 0.25)

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.1,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=0.0,
        dt=0.1,
    )

    assert np.allclose(result, field)


def test_simulation_with_proliferation_increases_total_mass() -> None:
    field = np.full((5, 5, 5), 0.1)

    params = ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.05,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=10.0,
        dt=0.5,
    )

    assert result.sum() > field.sum()
    assert np.all(result >= 0)
    assert np.all(result <= 1)
    
def test_symmetric_initial_condition_remains_symmetric() -> None:
    initial = gaussian_initial_condition(
        (31, 31, 31),
        center=(15.0, 15.0, 15.0),
        sigma=3.0,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.03,
    )

    result = simulate_reaction_diffusion(
        initial,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=10.0,
        dt=0.5,
    )

    assert np.allclose(result, np.flip(result, axis=0))
    assert np.allclose(result, np.flip(result, axis=1))
    assert np.allclose(result, np.flip(result, axis=2))

def test_brain_mask_prevents_diffusion_outside_domain() -> None:
    field = np.zeros((9, 9, 9), dtype=float)

    mask = np.zeros_like(field, dtype=bool)
    mask[2:7, 2:7, 2:7] = True

    field[3, 4, 4] = 1.0

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.0,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=5.0,
        dt=0.5,
        domain_mask=mask,
    )

    assert np.all(result[~mask] == 0.0)
    
def test_masked_diffusion_preserves_total_mass() -> None:
    field = np.zeros((9, 9, 9), dtype=float)

    mask = np.zeros_like(field, dtype=bool)
    mask[2:7, 2:7, 2:7] = True

    field[4, 4, 4] = 1.0

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.0,
    )

    result = simulate_reaction_diffusion(
        field,
        params,
        spacing=(1.0, 1.0, 1.0),
        duration_days=5.0,
        dt=0.5,
        domain_mask=mask,
    )

    assert np.isclose(
        result.sum(),
        field.sum(),
        atol=1e-10,
    )