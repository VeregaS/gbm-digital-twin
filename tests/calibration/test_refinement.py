import numpy as np
import pytest

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


def test_refined_axis_can_expand_upper_boundary_by_full_gap() -> None:
    result = build_refined_axis(
        [
            0.0,
            0.015,
            0.035,
            0.055,
        ],
        0.055,
        upper_boundary_expansion_factor=1.0,
    )

    assert result == [
        0.045,
        0.055,
        0.075,
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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[
        tuple[
            list[float],
            list[float],
        ]
    ] = []

    def fake_grid_search(
        initial_field: np.ndarray,
        observed_mask: np.ndarray,
        domain_mask: np.ndarray,
        *,
        spacing: tuple[float, float, float],
        duration_days: float,
        dt: float,
        diffusion_values: list[float],
        proliferation_values: list[float],
        threshold: float,
        volume_weight: float,
        treatment: object,
        start_time_day: float,
        cache_dir: object,
        workers: int,
        objective: str,
        soft_temperature: float,
    ) -> list[CalibrationResult]:
        del (
            initial_field,
            observed_mask,
            domain_mask,
            spacing,
            duration_days,
            dt,
            threshold,
            volume_weight,
            treatment,
            start_time_day,
            cache_dir,
            workers,
            objective,
            soft_temperature,
        )

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
            for proliferation in proliferation_values:
                loss = (
                    abs(diffusion - 0.005)
                    + abs(proliferation - 0.035)
                )

                results.append(
                    CalibrationResult(
                        diffusion=diffusion,
                        proliferation=proliferation,
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
    assert result.coarse_best.diffusion == 0.005
    assert result.coarse_best.proliferation == 0.035

    assert result.refined_diffusion_values == [
        0.0025,
        0.005,
        0.01,
    ]

    assert result.refined_proliferation_values == [
        0.025,
        0.035,
        0.045,
    ]


def test_iterative_search_can_move_beyond_single_upper_expansion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[
        tuple[
            list[float],
            list[float],
        ]
    ] = []

    def fake_grid_search(
        initial_field: np.ndarray,
        observed_mask: np.ndarray,
        domain_mask: np.ndarray,
        *,
        spacing: tuple[float, float, float],
        duration_days: float,
        dt: float,
        diffusion_values: list[float],
        proliferation_values: list[float],
        threshold: float,
        volume_weight: float,
        treatment: object,
        start_time_day: float,
        cache_dir: object,
        workers: int,
        objective: str,
        soft_temperature: float,
    ) -> list[CalibrationResult]:
        del (
            initial_field,
            observed_mask,
            domain_mask,
            spacing,
            duration_days,
            dt,
            threshold,
            volume_weight,
            treatment,
            start_time_day,
            cache_dir,
            workers,
            objective,
            soft_temperature,
        )

        calls.append(
            (
                list(diffusion_values),
                list(proliferation_values),
            )
        )

        results = [
            CalibrationResult(
                diffusion=diffusion,
                proliferation=proliferation,
                dice=(
                    1.0
                    - abs(diffusion - 0.060)
                    - abs(proliferation - 0.035)
                ),
                volume_error=0.0,
                loss=(
                    abs(diffusion - 0.060)
                    + abs(proliferation - 0.035)
                ),
            )
            for diffusion in diffusion_values
            for proliferation in proliferation_values
        ]

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
        refinement_rounds=3,
        upper_boundary_expansion_factor=1.0,
    )

    assert len(calls) == 4
    assert result.best.diffusion == pytest.approx(0.060)
    assert result.best.proliferation == pytest.approx(0.035)

    evaluated_diffusion = {
        value
        for diffusion_axis, _ in calls
        for value in diffusion_axis
    }

    assert max(evaluated_diffusion) >= 0.060


def test_adaptive_search_rejects_invalid_refinement_controls() -> None:
    initial = np.ones(
        (2, 2, 2),
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
        match="refinement_rounds",
    ):
        adaptive_grid_search(
            initial,
            observed,
            domain,
            spacing=(2.0, 2.0, 2.0),
            duration_days=10.0,
            dt=1.0,
            diffusion_values=[0.0, 0.01],
            proliferation_values=[0.0, 0.01],
            refinement_rounds=0,
        )

    with pytest.raises(
        ValueError,
        match="upper_boundary_expansion_factor",
    ):
        adaptive_grid_search(
            initial,
            observed,
            domain,
            spacing=(2.0, 2.0, 2.0),
            duration_days=10.0,
            dt=1.0,
            diffusion_values=[0.0, 0.01],
            proliferation_values=[0.0, 0.01],
            upper_boundary_expansion_factor=0.0,
        )
