import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    gaussian_initial_condition,
)


def test_gaussian_initial_condition() -> None:
    field = gaussian_initial_condition(
        (21, 21, 21),
        center=(10, 10, 10),
        sigma=2.0,
    )

    assert field.shape == (21, 21, 21)
    assert np.isclose(field[10, 10, 10], 1.0)
    assert np.all(field >= 0)
    assert np.all(field <= 1)


def test_reaction_diffusion_parameters() -> None:
    params = ReactionDiffusionParameters(
        diffusion=0.01,
        proliferation=0.02,
    )

    assert params.diffusion == 0.01
    assert params.proliferation == 0.02