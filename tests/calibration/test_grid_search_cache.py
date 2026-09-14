from pathlib import Path

import numpy as np
import pytest

import gbm_twin.calibration.grid_search as grid_search_module
from gbm_twin.calibration.grid_search import (
    grid_search,
)


def test_grid_search_reuses_cached_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = 0

    def fake_simulate(
        initial_field,
        params,
        *,
        spacing,
        duration_days,
        dt,
        domain_mask,
        treatment,
        start_time_day,
    ):
        nonlocal calls

        calls += 1

        return initial_field.copy()

    monkeypatch.setattr(
        grid_search_module,
        "simulate_reaction_diffusion",
        fake_simulate,
    )

    initial = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    initial[
        1:4,
        1:4,
        1:4,
    ] = 1.0

    observed = (
        initial
        >= 0.5
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    kwargs = {
        "spacing": (
            2.0,
            2.0,
            2.0,
        ),
        "duration_days": 10.0,
        "dt": 1.0,
        "diffusion_values": [0.01],
        "proliferation_values": [0.03],
        "threshold": 0.5,
        "volume_weight": 0.5,
        "cache_dir": tmp_path,
    }

    first = grid_search(
        initial,
        observed,
        domain,
        **kwargs,
    )

    assert calls == 1

    second = grid_search(
        initial,
        observed,
        domain,
        **kwargs,
    )

    assert calls == 1
    assert second == first


def test_cache_distinguishes_parameters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls = 0

    def fake_simulate(
        initial_field,
        params,
        *,
        spacing,
        duration_days,
        dt,
        domain_mask,
        treatment,
        start_time_day,
    ):
        nonlocal calls

        calls += 1

        return initial_field.copy()

    monkeypatch.setattr(
        grid_search_module,
        "simulate_reaction_diffusion",
        fake_simulate,
    )

    initial = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    initial[
        1:4,
        1:4,
        1:4,
    ] = 1.0

    observed = (
        initial
        >= 0.5
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    grid_search(
        initial,
        observed,
        domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=10.0,
        dt=1.0,
        diffusion_values=[0.01],
        proliferation_values=[0.03],
        cache_dir=tmp_path,
    )

    grid_search(
        initial,
        observed,
        domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=10.0,
        dt=1.0,
        diffusion_values=[0.02],
        proliferation_values=[0.03],
        cache_dir=tmp_path,
    )

    assert calls == 2
    
def test_grid_search_rejects_invalid_workers() -> None:
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
        match="workers",
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
            workers=0,
        )