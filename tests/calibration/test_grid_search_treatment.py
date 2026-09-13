import math

import numpy as np
import pytest

from gbm_twin.calibration.grid_search import (
    grid_search,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
)


def test_grid_search_uses_fractionated_treatment() -> None:
    initial = np.zeros(
        (3, 3, 3),
        dtype=float,
    )

    initial[
        1,
        1,
        1,
    ] = 1.0

    initial[
        1,
        1,
        2,
    ] = 0.7

    observed = np.zeros(
        (3, 3, 3),
        dtype=bool,
    )

    observed[
        1,
        1,
        1,
    ] = True

    domain = np.ones(
        (3, 3, 3),
        dtype=bool,
    )

    alpha = (
        math.log(2.0)
        / 2.0
    )

    treatment = (
        FractionatedRadiotherapy(
            fraction_days=(1.0,),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=alpha,
            beta_per_gy2=0.0,
        )
    )

    untreated_results = grid_search(
        initial,
        observed,
        domain,
        spacing=(
            1.0,
            1.0,
            1.0,
        ),
        duration_days=2.0,
        dt=2.0,
        diffusion_values=[0.0],
        proliferation_values=[0.0],
        threshold=0.5,
        volume_weight=0.5,
    )

    treated_results = grid_search(
        initial,
        observed,
        domain,
        spacing=(
            1.0,
            1.0,
            1.0,
        ),
        duration_days=2.0,
        dt=2.0,
        diffusion_values=[0.0],
        proliferation_values=[0.0],
        threshold=0.5,
        volume_weight=0.5,
        treatment=treatment,
    )

    untreated = (
        untreated_results[0]
    )

    treated = (
        treated_results[0]
    )

    assert untreated.dice < 1.0

    assert treated.dice == pytest.approx(
        1.0
    )

    assert (
        treated.volume_error
        == pytest.approx(0.0)
    )

    assert (
        treated.loss
        < untreated.loss
    )


def test_grid_search_rejects_negative_start_time() -> None:
    initial = np.ones(
        (3, 3, 3),
        dtype=float,
    )

    observed = np.ones(
        (3, 3, 3),
        dtype=bool,
    )

    domain = np.ones(
        (3, 3, 3),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="start_time_day",
    ):
        grid_search(
            initial,
            observed,
            domain,
            spacing=(
                1.0,
                1.0,
                1.0,
            ),
            duration_days=1.0,
            dt=1.0,
            diffusion_values=[0.0],
            proliferation_values=[0.0],
            start_time_day=-1.0,
        )