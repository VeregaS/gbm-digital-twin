from dataclasses import dataclass

import numpy as np

from gbm_twin.evaluation.metrics import (
    dice_score,
    relative_volume_error,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    TreatmentWindow,
)

TreatmentModel = (
    TreatmentWindow
    | FractionatedRadiotherapy
)


@dataclass(frozen=True)
class CalibrationResult:
    diffusion: float
    proliferation: float
    dice: float
    volume_error: float
    loss: float


def grid_search(
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
) -> list[CalibrationResult]:
    if initial_field.shape != observed_mask.shape:
        raise ValueError(
            "Initial field and observed mask "
            "must have the same shape"
        )

    if initial_field.shape != domain_mask.shape:
        raise ValueError(
            "Initial field and domain mask "
            "must have the same shape"
        )

    if duration_days < 0:
        raise ValueError(
            "duration_days must be non-negative"
        )

    if dt <= 0:
        raise ValueError(
            "dt must be positive"
        )

    if not (
        0.0
        <= threshold
        <= 1.0
    ):
        raise ValueError(
            "threshold must be within [0, 1]"
        )

    if volume_weight < 0:
        raise ValueError(
            "volume_weight must be non-negative"
        )

    if not diffusion_values:
        raise ValueError(
            "diffusion_values must not be empty"
        )

    if not proliferation_values:
        raise ValueError(
            "proliferation_values must not be empty"
        )

    if start_time_day < 0:
        raise ValueError(
            "start_time_day must be non-negative"
        )

    observed = np.asarray(
        observed_mask,
        dtype=bool,
    )

    domain = np.asarray(
        domain_mask,
        dtype=bool,
    )

    results: list[
        CalibrationResult
    ] = []

    for diffusion in diffusion_values:
        for proliferation in (
            proliferation_values
        ):
            print(
                f"Running D={diffusion:.4f}, "
                f"rho={proliferation:.4f}..."
            )

            params = (
                ReactionDiffusionParameters(
                    diffusion=diffusion,
                    proliferation=proliferation,
                )
            )

            simulated = (
                simulate_reaction_diffusion(
                    initial_field,
                    params,
                    spacing=spacing,
                    duration_days=(
                        duration_days
                    ),
                    dt=dt,
                    domain_mask=domain,
                    treatment=treatment,
                    start_time_day=(
                        start_time_day
                    ),
                )
            )

            predicted = (
                simulated
                >= threshold
            )

            dice = dice_score(
                predicted,
                observed,
            )

            volume_error = (
                relative_volume_error(
                    predicted,
                    observed,
                )
            )

            loss = (
                1.0
                - dice
                + volume_weight
                * volume_error
            )

            result = CalibrationResult(
                diffusion=diffusion,
                proliferation=proliferation,
                dice=dice,
                volume_error=(
                    volume_error
                ),
                loss=loss,
            )

            results.append(
                result
            )

            print(
                f"  Dice={dice:.4f} "
                f"VolumeError="
                f"{volume_error:.2%} "
                f"Loss={loss:.4f}"
            )

    results.sort(
        key=lambda result: result.loss
    )

    return results