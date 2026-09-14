import numpy as np
import pytest

import gbm_twin.calibration.grid_search as grid_search_module
from gbm_twin.calibration.grid_search import (
    grid_search,
)


def test_soft_objective_breaks_hard_empty_plateau(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initial = np.zeros(
        (3, 3, 3),
        dtype=np.float32,
    )

    observed = np.zeros(
        initial.shape,
        dtype=bool,
    )

    observed[
        1,
        1,
        1,
    ] = True

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    def fake_simulate(
        initial_field,
        params,
        **kwargs,
    ):
        result = np.zeros_like(
            initial_field,
            dtype=np.float32,
        )

        if params.proliferation == 0.01:
            value = 0.10
        else:
            value = 0.49

        result[
            1,
            1,
            1,
        ] = value

        return result

    monkeypatch.setattr(
        grid_search_module,
        "simulate_reaction_diffusion",
        fake_simulate,
    )

    hard = grid_search(
        initial,
        observed,
        domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=1.0,
        diffusion_values=[0.0],
        proliferation_values=[
            0.01,
            0.02,
        ],
        objective="hard",
        workers=1,
    )

    soft = grid_search(
        initial,
        observed,
        domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=1.0,
        diffusion_values=[0.0],
        proliferation_values=[
            0.01,
            0.02,
        ],
        objective="soft",
        soft_temperature=0.05,
        workers=1,
    )

    assert (
        hard[0].proliferation
        == 0.01
    )

    assert (
        soft[0].proliferation
        == 0.02
    )

    assert (
        soft[0].loss
        < soft[1].loss
    )


def test_grid_search_rejects_invalid_soft_temperature() -> None:
    initial = np.ones(
        (3, 3, 3),
        dtype=np.float32,
    )

    observed = np.ones(
        initial.shape,
        dtype=bool,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="soft_temperature",
    ):
        grid_search(
            initial,
            observed,
            domain,
            spacing=(2.0, 2.0, 2.0),
            duration_days=1.0,
            dt=1.0,
            diffusion_values=[0.01],
            proliferation_values=[0.03],
            objective="soft",
            soft_temperature=0.0,
        )