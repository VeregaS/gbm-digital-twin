import numpy as np

from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import (
    explicit_stability_limit,
    laplacian_3d,
    reaction_diffusion_step,
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
        params.diffusion,
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