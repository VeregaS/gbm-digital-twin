from __future__ import annotations

import math

import numpy as np

from gbm_twin.models.pirt import (
    apply_pirt_fraction,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)

_TIME_TOLERANCE = 1e-9


def _validate_fraction_days(
    fraction_days: tuple[float, ...],
) -> None:
    if any(
        not math.isfinite(day)
        for day in fraction_days
    ):
        raise ValueError(
            "fraction_days must contain only finite values"
        )

    if any(
        current <= previous
        for previous, current in zip(
            fraction_days,
            fraction_days[1:],
            strict=False,
        )
    ):
        raise ValueError(
            "fraction_days must be strictly increasing"
        )


def simulate_reaction_diffusion_pirt(
    initial_field: np.ndarray,
    parameters: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    domain_mask: np.ndarray,
    fraction_days: tuple[float, ...],
    survival_fraction: float,
    start_time_day: float = 0.0,
    crop_to_domain: bool = True,
) -> np.ndarray:
    """
    Simulate reaction-diffusion growth with discrete PIRT fractions.

    Fraction days are absolute simulation times, using the same time
    convention as the existing treatment model.

    Between fractions the standard reaction-diffusion solver is used.
    At each fraction:

        c <- c - (1 - S) * c * (1 - c)

    where S is the LQ surviving fraction.
    """

    if duration_days < 0:
        raise ValueError(
            "duration_days must be non-negative"
        )

    if dt <= 0:
        raise ValueError(
            "dt must be positive"
        )

    if not math.isfinite(
        start_time_day
    ):
        raise ValueError(
            "start_time_day must be finite"
        )

    _validate_fraction_days(
        fraction_days
    )

    end_time_day = (
        start_time_day
        + duration_days
    )

    field = np.asarray(
        initial_field
    ).copy()

    current_time = (
        start_time_day
    )

    active_fraction_days = tuple(
        day
        for day in fraction_days
        if (
            day
            >= start_time_day
            - _TIME_TOLERANCE
            and day
            <= end_time_day
            + _TIME_TOLERANCE
        )
    )

    for fraction_day in active_fraction_days:
        segment_duration = (
            fraction_day
            - current_time
        )

        if (
            segment_duration
            > _TIME_TOLERANCE
        ):
            field = simulate_reaction_diffusion(
                field,
                parameters,
                spacing=spacing,
                duration_days=segment_duration,
                dt=dt,
                domain_mask=domain_mask,
                treatment=None,
                start_time_day=current_time,
                crop_to_domain=crop_to_domain,
            )

        field = apply_pirt_fraction(
            field,
            survival_fraction=survival_fraction,
            domain_mask=domain_mask,
        )

        current_time = fraction_day

    remaining_duration = (
        end_time_day
        - current_time
    )

    if (
        remaining_duration
        > _TIME_TOLERANCE
    ):
        field = simulate_reaction_diffusion(
            field,
            parameters,
            spacing=spacing,
            duration_days=remaining_duration,
            dt=dt,
            domain_mask=domain_mask,
            treatment=None,
            start_time_day=current_time,
            crop_to_domain=crop_to_domain,
        )

    return field