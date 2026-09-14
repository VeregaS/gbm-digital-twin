import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)


def parameters() -> ReactionDiffusionParameters:
    return ReactionDiffusionParameters(
        diffusion=0.01,
        proliferation=0.03,
    )


def test_solver_preserves_float32() -> None:
    initial = np.full(
        (7, 7, 7),
        0.25,
        dtype=np.float32,
    )

    result = simulate_reaction_diffusion(
        initial,
        parameters(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
    )

    assert result.dtype == np.float32


def test_solver_preserves_float64() -> None:
    initial = np.full(
        (7, 7, 7),
        0.25,
        dtype=np.float64,
    )

    result = simulate_reaction_diffusion(
        initial,
        parameters(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
    )

    assert result.dtype == np.float64


def test_integer_initial_field_uses_float64() -> None:
    initial = np.zeros(
        (7, 7, 7),
        dtype=np.uint8,
    )

    initial[
        2:5,
        2:5,
        2:5,
    ] = 1

    result = simulate_reaction_diffusion(
        initial,
        parameters(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=2.0,
        dt=1.0,
    )

    assert result.dtype == np.float64