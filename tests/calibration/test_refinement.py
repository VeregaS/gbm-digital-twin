import numpy as np

import gbm_twin.calibration.refinement as refinement_module
from gbm_twin.calibration.grid_search import (
    CalibrationResult,
)
from gbm_twin.calibration.refinement import (
    adaptive_grid_search,
    build_refined_axis,
)


def test_refined_axis_for_interior_point() -> None:
    result = build_refined_axis(
        [
            0.0,
            0.005,
            0.015,
            0.030,
        ],
        0.005,
    )

    assert result == [
        0.0025,
        0.005,
        0.01,
    ]


def test_refined_axis_extends_upper_boundary() -> None:
    result = build_refined_axis(
        [
            0.0,
            0.015,
            0.035,
            0.055,
        ],
        0.055,
    )

    assert result == [
        0.045,
        0.055,
        0.065,
    ]


def test_refined_axis_respects_zero_lower_boundary() -> None:
    result = build_refined_axis(
        [
            0.0,
            0.005,
            0.015,
        ],
        0.0,
    )

    assert result == [
        0.0,
        0.0025,
    ]


def test_adaptive_search_refines_around_coarse_best(
    monkeypatch,
) -> None:
    calls: list[
        tuple[
            list[float],
            list[float],
        ]
    ] = []

    def fake_grid_search(
        initial_field,
        observed_mask,
        domain_mask,
        *,
        spacing,
        duration_days,
        dt,
        diffusion_values,
        proliferation_values,
        threshold,
        volume_weight,
        treatment,
        start_time_day,
        cache_dir,
        workers,
        objective,
        soft_temperature,
    ):
        calls.append(
            (
                list(diffusion_values),
                list(proliferation_values),
            )
        )

        results: list[
            CalibrationResult
        ] = []

        for diffusion in diffusion_values:
            for proliferation in (
                proliferation_values
            ):
                loss = (
                    abs(
                        diffusion
                        - 0.005
                    )
                    + abs(
                        proliferation
                        - 0.035
                    )
                )

                results.append(
                    CalibrationResult(
                        diffusion=diffusion,
                        proliferation=(
                            proliferation
                        ),
                        dice=1.0 - loss,
                        volume_error=0.0,
                        loss=loss,
                    )
                )

        results.sort(
            key=lambda result: result.loss
        )

        return results

    monkeypatch.setattr(
        refinement_module,
        "grid_search",
        fake_grid_search,
    )

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

    result = adaptive_grid_search(
        initial,
        observed,
        domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=10.0,
        dt=1.0,
        diffusion_values=[
            0.0,
            0.005,
            0.015,
            0.030,
        ],
        proliferation_values=[
            0.0,
            0.015,
            0.035,
            0.055,
        ],
    )

    assert len(calls) == 2

    assert (
        result.coarse_best.diffusion
        == 0.005
    )

    assert (
        result.coarse_best.proliferation
        == 0.035
    )

    assert (
        result.refined_diffusion_values
        == [
            0.0025,
            0.005,
            0.01,
        ]
    )

    assert (
        result.refined_proliferation_values
        == [
            0.025,
            0.035,
            0.045,
        ]
    )