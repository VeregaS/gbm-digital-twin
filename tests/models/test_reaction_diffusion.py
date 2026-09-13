import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    build_computational_domain,
    gaussian_initial_condition,
    initial_condition_from_gtv,
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
    
def test_initial_condition_from_gtv() -> None:
    gtv = np.zeros((10, 10, 10))
    brain = np.zeros((10, 10, 10))

    brain[1:9, 1:9, 1:9] = 1
    gtv[4:6, 4:6, 4:6] = 1

    domain = build_computational_domain(brain, gtv)
    field = initial_condition_from_gtv(gtv, domain)

    assert field.shape == gtv.shape
    assert np.all(field[gtv == 1] == 1.0)
    assert np.all(field[brain == 0] == 0.0)
    
def test_computational_domain_contains_gtv() -> None:
    brain = np.zeros((10, 10, 10))
    gtv = np.zeros((10, 10, 10))

    brain[2:8, 2:8, 2:8] = 1

    gtv[1:4, 4:6, 4:6] = 1

    domain = build_computational_domain(brain, gtv)

    assert np.all(domain[gtv > 0.5])
    assert np.all(domain[brain > 0.5])