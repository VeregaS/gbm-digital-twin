from dataclasses import dataclass

import numpy as np

from gbm_twin.evaluation.metrics import (
    dice_score,
    relative_volume_error,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import simulate_reaction_diffusion


@dataclass(frozen=True)
class CalibrationResult:
    diffusion: float
    proliferation: float
    dice: float
    volume_error: float
    loss: float


def grid_search(
    initial: np.ndarray,
    observed: np.ndarray,
    domain: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    diffusion_values: list[float],
    proliferation_values: list[float],
    threshold: float = 0.5,
    volume_weight: float = 0.5,
) -> list[CalibrationResult]:
    results: list[CalibrationResult] = []

    for diffusion in diffusion_values:
        for proliferation in proliferation_values:
            print(
                f"Running D={diffusion:.4f}, "
                f"rho={proliferation:.4f}..."
            )

            params = ReactionDiffusionParameters(
                diffusion=diffusion,
                proliferation=proliferation,
            )

            concentration = simulate_reaction_diffusion(
                initial,
                params,
                spacing=spacing,
                duration_days=duration_days,
                dt=dt,
                domain_mask=domain,
            )

            predicted = concentration >= threshold

            dice = dice_score(
                predicted,
                observed,
            )

            volume_error = relative_volume_error(
                predicted,
                observed,
            )

            loss = (
                (1.0 - dice)
                + volume_weight * volume_error
            )

            print(
                f"  Dice={dice:.4f} "
                f"VolumeError={volume_error * 100:.2f}% "
                f"Loss={loss:.4f}"
            )

            results.append(
                CalibrationResult(
                    diffusion=diffusion,
                    proliferation=proliferation,
                    dice=dice,
                    volume_error=volume_error,
                    loss=loss,
                )
            )

    return sorted(
        results,
        key=lambda result: result.loss,
    )