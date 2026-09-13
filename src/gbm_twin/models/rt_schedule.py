from dataclasses import dataclass

from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
)

WEEKDAY_LIKE_ASSUMPTION = (
    "reconstructed_5_daily_fractions_then_2_day_gap"
)


@dataclass(frozen=True)
class ReconstructedRadiotherapySchedule:
    start_day: float
    total_dose_gy: float
    fractions_number: int
    dose_per_fraction_gy: float
    fraction_days: tuple[float, ...]
    assumption: str


def reconstruct_weekday_like_schedule(
    *,
    start_day: float,
    total_dose_gy: float,
    fractions_number: int,
) -> ReconstructedRadiotherapySchedule:
    if start_day < 0:
        raise ValueError(
            "RT start day must be non-negative"
        )

    if total_dose_gy <= 0:
        raise ValueError(
            "Total RT dose must be positive"
        )

    if fractions_number <= 0:
        raise ValueError(
            "Fractions number must be positive"
        )

    fractions_per_block = 5
    gap_days = 2

    fraction_days: list[float] = []

    for index in range(
        fractions_number
    ):
        block_index = (
            index
            // fractions_per_block
        )

        position_in_block = (
            index
            % fractions_per_block
        )

        day = (
            start_day
            + block_index
            * (
                fractions_per_block
                + gap_days
            )
            + position_in_block
        )

        fraction_days.append(
            float(day)
        )

    dose_per_fraction_gy = (
        total_dose_gy
        / fractions_number
    )

    return ReconstructedRadiotherapySchedule(
        start_day=start_day,
        total_dose_gy=total_dose_gy,
        fractions_number=fractions_number,
        dose_per_fraction_gy=(
            dose_per_fraction_gy
        ),
        fraction_days=tuple(
            fraction_days
        ),
        assumption=(
            WEEKDAY_LIKE_ASSUMPTION
        ),
    )


def build_fractionated_radiotherapy(
    schedule: ReconstructedRadiotherapySchedule,
    radiobiology: RadiobiologyParameters,
) -> FractionatedRadiotherapy:
    return FractionatedRadiotherapy(
        fraction_days=(
            schedule.fraction_days
        ),
        dose_per_fraction_gy=(
            schedule.dose_per_fraction_gy
        ),
        alpha_per_gy=(
            radiobiology.alpha_per_gy
        ),
        beta_per_gy2=(
            radiobiology.beta_per_gy2
        ),
    )