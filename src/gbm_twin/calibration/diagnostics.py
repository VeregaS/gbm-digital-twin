from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from gbm_twin.calibration.grid_search import CalibrationResult

_FLOAT_TOLERANCE = 1e-12


@dataclass(frozen=True)
class CalibrationDiagnostics:
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool
    diffusion_bracketed: bool
    proliferation_bracketed: bool
    identifiable: bool


def _same_value(
    first: float,
    second: float,
) -> bool:
    return math.isclose(
        first,
        second,
        rel_tol=0.0,
        abs_tol=_FLOAT_TOLERANCE,
    )


def _parameter_key(
    candidate: CalibrationResult,
) -> tuple[float, float]:
    return (
        round(candidate.diffusion, 12),
        round(candidate.proliferation, 12),
    )


def _unique_candidate_losses(
    candidates: Sequence[CalibrationResult],
) -> dict[tuple[float, float], float]:
    losses: dict[
        tuple[float, float],
        float,
    ] = {}

    for candidate in candidates:
        key = _parameter_key(
            candidate
        )

        current = losses.get(
            key
        )

        if (
            current is None
            or candidate.loss < current
        ):
            losses[key] = (
                candidate.loss
            )

    return losses


def _is_bracketed(
    value: float,
    evaluated_values: Sequence[float],
) -> bool:
    has_lower = any(
        candidate
        < value - _FLOAT_TOLERANCE
        for candidate in evaluated_values
    )

    has_upper = any(
        candidate
        > value + _FLOAT_TOLERANCE
        for candidate in evaluated_values
    )

    return (
        has_lower
        and has_upper
    )


def _is_at_boundary(
    value: float,
    evaluated_values: Sequence[float],
) -> bool:
    minimum = min(
        evaluated_values
    )

    maximum = max(
        evaluated_values
    )

    return (
        _same_value(
            value,
            minimum,
        )
        or _same_value(
            value,
            maximum,
        )
    )


def assess_calibration_diagnostics(
    *,
    best: CalibrationResult,
    candidates: Sequence[CalibrationResult],
) -> CalibrationDiagnostics:
    if not candidates:
        raise ValueError(
            "Calibration diagnostics require at least one candidate"
        )

    candidate_losses = (
        _unique_candidate_losses(
            candidates
        )
    )

    best_key = _parameter_key(
        best
    )

    if best_key not in candidate_losses:
        raise ValueError(
            "Best calibration result must be present in candidates"
        )

    best_loss = candidate_losses[
        best_key
    ]

    minimum_loss = min(
        candidate_losses.values()
    )

    if not _same_value(
        best_loss,
        minimum_loss,
    ):
        raise ValueError(
            "Best calibration result does not have minimum loss"
        )

    diffusion_values = tuple(
        sorted(
            {
                key[0]
                for key in candidate_losses
            }
        )
    )

    proliferation_values = tuple(
        sorted(
            {
                key[1]
                for key in candidate_losses
            }
        )
    )

    diffusion_at_boundary = (
        _is_at_boundary(
            best.diffusion,
            diffusion_values,
        )
    )

    proliferation_at_boundary = (
        _is_at_boundary(
            best.proliferation,
            proliferation_values,
        )
    )

    diffusion_bracketed = (
        _is_bracketed(
            best.diffusion,
            diffusion_values,
        )
    )

    proliferation_bracketed = (
        _is_bracketed(
            best.proliferation,
            proliferation_values,
        )
    )

    tied_best_count = sum(
        1
        for loss in candidate_losses.values()
        if _same_value(
            loss,
            minimum_loss,
        )
    )

    identifiable = (
        diffusion_bracketed
        and proliferation_bracketed
        and tied_best_count == 1
    )

    return CalibrationDiagnostics(
        diffusion_at_boundary=(
            diffusion_at_boundary
        ),
        proliferation_at_boundary=(
            proliferation_at_boundary
        ),
        diffusion_bracketed=(
            diffusion_bracketed
        ),
        proliferation_bracketed=(
            proliferation_bracketed
        ),
        identifiable=identifiable,
    )