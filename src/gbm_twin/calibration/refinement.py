from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.calibration.grid_search import (
    CalibrationObjective,
    CalibrationResult,
    grid_search,
)
from gbm_twin.models.solver import (
    TreatmentModel,
)


@dataclass(frozen=True)
class AdaptiveCalibrationResult:
    best: CalibrationResult
    coarse_best: CalibrationResult
    coarse_results: list[CalibrationResult]
    refined_results: list[CalibrationResult]
    refined_diffusion_values: list[float]
    refined_proliferation_values: list[float]


def build_refined_axis(
    values: list[float],
    best_value: float,
    *,
    minimum: float = 0.0,
    upper_boundary_expansion_factor: float = 0.5,
) -> list[float]:
    if len(values) < 2:
        raise ValueError(
            "At least two coarse values are required"
        )

    if upper_boundary_expansion_factor <= 0.0:
        raise ValueError(
            "upper_boundary_expansion_factor must be positive"
        )

    ordered = sorted(
        set(float(value) for value in values)
    )

    if best_value not in ordered:
        raise ValueError(
            "best_value must be present in coarse values"
        )

    index = ordered.index(
        best_value
    )

    if index > 0:
        left_gap = (
            best_value
            - ordered[index - 1]
        )

        left = (
            best_value
            - left_gap / 2.0
        )
    else:
        right_gap = (
            ordered[1]
            - best_value
        )

        left = best_value

        if best_value > minimum:
            left = max(
                minimum,
                best_value
                - right_gap / 2.0,
            )

    if index < len(ordered) - 1:
        right_gap = (
            ordered[index + 1]
            - best_value
        )

        right = (
            best_value
            + right_gap / 2.0
        )
    else:
        left_gap = (
            best_value
            - ordered[index - 1]
        )

        right = (
            best_value
            + left_gap
            * upper_boundary_expansion_factor
        )

    candidates = {
        round(float(best_value), 12),
        round(
            float(max(minimum, left)),
            12,
        ),
        round(
            float(max(minimum, right)),
            12,
        ),
    }

    return sorted(
        candidates
    )


def _result_key(
    result: CalibrationResult,
) -> tuple[float, float]:
    return (
        round(float(result.diffusion), 12),
        round(float(result.proliferation), 12),
    )


def _deduplicate_results(
    results: list[CalibrationResult],
) -> list[CalibrationResult]:
    by_parameters: dict[
        tuple[float, float],
        CalibrationResult,
    ] = {}

    for result in results:
        key = _result_key(
            result
        )

        existing = by_parameters.get(
            key
        )

        if (
            existing is None
            or result.loss < existing.loss
        ):
            by_parameters[key] = result

    return sorted(
        by_parameters.values(),
        key=lambda result: result.loss,
    )


def adaptive_grid_search(
    initial_field: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    diffusion_values: list[float],
    proliferation_values: list[float],
    threshold: float = 0.5,
    volume_weight: float = 0.5,
    treatment: TreatmentModel | None = None,
    start_time_day: float = 0.0,
    cache_dir: Path | None = None,
    workers: int = 1,
    objective: CalibrationObjective = "hard",
    soft_temperature: float = 0.05,
    refinement_rounds: int = 1,
    upper_boundary_expansion_factor: float = 0.5,
) -> AdaptiveCalibrationResult:
    if refinement_rounds < 1:
        raise ValueError(
            "refinement_rounds must be at least 1"
        )

    if upper_boundary_expansion_factor <= 0.0:
        raise ValueError(
            "upper_boundary_expansion_factor must be positive"
        )

    coarse_results = grid_search(
        initial_field,
        observed_mask,
        domain_mask,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
        diffusion_values=diffusion_values,
        proliferation_values=(
            proliferation_values
        ),
        threshold=threshold,
        volume_weight=volume_weight,
        treatment=treatment,
        start_time_day=start_time_day,
        cache_dir=cache_dir,
        workers=workers,
        objective=objective,
        soft_temperature=soft_temperature,
    )

    coarse_best = coarse_results[0]

    all_results = list(
        coarse_results
    )

    refined_results: list[
        CalibrationResult
    ] = []

    evaluated_diffusion_values = sorted(
        {
            float(result.diffusion)
            for result in coarse_results
        }
    )

    evaluated_proliferation_values = sorted(
        {
            float(result.proliferation)
            for result in coarse_results
        }
    )

    refined_diffusion_values: list[float] = []
    refined_proliferation_values: list[float] = []

    for round_index in range(
        refinement_rounds
    ):
        current_best = (
            _deduplicate_results(
                all_results
            )[0]
        )

        refined_diffusion_values = (
            build_refined_axis(
                evaluated_diffusion_values,
                current_best.diffusion,
                upper_boundary_expansion_factor=(
                    upper_boundary_expansion_factor
                ),
            )
        )

        refined_proliferation_values = (
            build_refined_axis(
                evaluated_proliferation_values,
                current_best.proliferation,
                upper_boundary_expansion_factor=(
                    upper_boundary_expansion_factor
                ),
            )
        )

        print()
        print("=" * 60)
        print(
            "LOCAL REFINEMENT "
            f"{round_index + 1}/{refinement_rounds}"
        )
        print("=" * 60)

        print(
            "D:",
            refined_diffusion_values,
        )

        print(
            "rho:",
            refined_proliferation_values,
        )

        round_results = grid_search(
            initial_field,
            observed_mask,
            domain_mask,
            spacing=spacing,
            duration_days=duration_days,
            dt=dt,
            diffusion_values=(
                refined_diffusion_values
            ),
            proliferation_values=(
                refined_proliferation_values
            ),
            threshold=threshold,
            volume_weight=volume_weight,
            treatment=treatment,
            start_time_day=start_time_day,
            cache_dir=cache_dir,
            workers=workers,
            objective=objective,
            soft_temperature=soft_temperature,
        )

        refined_results.extend(
            round_results
        )

        all_results.extend(
            round_results
        )

        evaluated_diffusion_values = sorted(
            {
                *evaluated_diffusion_values,
                *refined_diffusion_values,
            }
        )

        evaluated_proliferation_values = sorted(
            {
                *evaluated_proliferation_values,
                *refined_proliferation_values,
            }
        )

    combined = _deduplicate_results(
        all_results
    )

    return AdaptiveCalibrationResult(
        best=combined[0],
        coarse_best=coarse_best,
        coarse_results=coarse_results,
        refined_results=(
            _deduplicate_results(
                refined_results
            )
        ),
        refined_diffusion_values=(
            refined_diffusion_values
        ),
        refined_proliferation_values=(
            refined_proliferation_values
        ),
    )
