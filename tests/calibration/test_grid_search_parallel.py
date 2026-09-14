import numpy as np

from gbm_twin.calibration.grid_search import (
    grid_search,
)


def test_parallel_grid_search_matches_sequential() -> None:
    shape = (
        9,
        9,
        9,
    )

    initial = np.zeros(
        shape,
        dtype=np.float32,
    )

    initial[
        3:6,
        3:6,
        3:6,
    ] = 1.0

    observed = initial >= 0.5

    domain = np.ones(
        shape,
        dtype=bool,
    )

    kwargs = {
        "spacing": (
            2.0,
            2.0,
            2.0,
        ),
        "duration_days": 2.0,
        "dt": 1.0,
        "diffusion_values": [
            0.0,
            0.01,
        ],
        "proliferation_values": [
            0.0,
            0.03,
        ],
    }

    sequential = grid_search(
        initial,
        observed,
        domain,
        workers=1,
        **kwargs,
    )

    parallel = grid_search(
        initial,
        observed,
        domain,
        workers=2,
        **kwargs,
    )

    assert parallel == sequential