import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)


def test_domain_cropping_matches_full_solver() -> None:
    shape = (
        30,
        32,
        28,
    )

    coordinates = np.indices(
        shape,
        dtype=np.float32,
    )

    center = np.asarray(
        [
            (size - 1) / 2.0
            for size in shape
        ],
        dtype=np.float32,
    )

    distance_squared = np.zeros(
        shape,
        dtype=np.float32,
    )

    for axis in range(3):
        distance_squared += (
            (
                coordinates[axis]
                - center[axis]
            )
            / 5.0
        ) ** 2

    initial = np.exp(
        -0.5
        * distance_squared
    ).astype(
        np.float32
    )

    domain = np.zeros(
        shape,
        dtype=bool,
    )

    domain[
        4:26,
        5:27,
        3:25,
    ] = True

    initial[
        ~domain
    ] = 0.0

    params = ReactionDiffusionParameters(
        diffusion=0.01,
        proliferation=0.04,
    )

    full = simulate_reaction_diffusion(
        initial,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=20.0,
        dt=2.0,
        domain_mask=domain,
        crop_to_domain=False,
    )

    cropped = simulate_reaction_diffusion(
        initial,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=20.0,
        dt=2.0,
        domain_mask=domain,
        crop_to_domain=True,
    )

    np.testing.assert_allclose(
        cropped,
        full,
        rtol=0.0,
        atol=0.0,
    )