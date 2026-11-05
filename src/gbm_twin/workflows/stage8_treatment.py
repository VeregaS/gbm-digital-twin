from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np

from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.rt_schedule import ReconstructedRadiotherapySchedule
from gbm_twin.models.spatial_radiotherapy import (
    DoseNormalizationResult,
    lq_survival_field,
    normalize_cumulative_rtdose_to_gy,
    per_fraction_dose_from_cumulative_plan,
)
from gbm_twin.models.treatment_memory import FractionResponseEvent


@dataclass(frozen=True)
class Stage8RadiotherapyEvents:
    events: tuple[FractionResponseEvent, ...]
    spatial_dose: bool
    proliferation_survival: float
    dose_normalization: DoseNormalizationResult | None


def _uniform_lq_survival(
    dose_per_fraction_gy: float,
    radiobiology: RadiobiologyParameters,
) -> float:
    exponent = -(
        radiobiology.alpha_per_gy * dose_per_fraction_gy
        + radiobiology.beta_per_gy2 * dose_per_fraction_gy**2
    )
    return math.exp(exponent)


def build_stage8_radiotherapy_events(
    schedule: ReconstructedRadiotherapySchedule,
    radiobiology: RadiobiologyParameters,
    *,
    proliferation_survival: float,
    cumulative_rtdose: np.ndarray | None = None,
    cumulative_rtdose_unit: Literal["auto", "gy", "cgy"] = "auto",
) -> Stage8RadiotherapyEvents:
    """Build fraction events with immediate PIRT and persistent growth memory.

    When a cumulative RTDOSE map is supplied, the immediate LQ survival is
    spatial. The cumulative plan is converted to one-fraction dose under the
    explicit same-relative-dose-distribution-per-fraction assumption.
    """

    if not 0.0 < proliferation_survival <= 1.0:
        raise ValueError("proliferation_survival must be within (0, 1]")

    normalization: DoseNormalizationResult | None = None

    if cumulative_rtdose is None:
        immediate_survival: float | np.ndarray = _uniform_lq_survival(
            schedule.dose_per_fraction_gy,
            radiobiology,
        )
        spatial = False
    else:
        normalization = normalize_cumulative_rtdose_to_gy(
            cumulative_rtdose,
            prescribed_total_dose_gy=schedule.total_dose_gy,
            unit=cumulative_rtdose_unit,
        )
        fraction_dose = per_fraction_dose_from_cumulative_plan(
            normalization.dose_gy,
            prescribed_total_dose_gy=schedule.total_dose_gy,
            dose_per_fraction_gy=schedule.dose_per_fraction_gy,
        )
        immediate_survival = lq_survival_field(
            fraction_dose,
            alpha_per_gy=radiobiology.alpha_per_gy,
            beta_per_gy2=radiobiology.beta_per_gy2,
        )
        spatial = True

    events = tuple(
        FractionResponseEvent(
            day=fraction_day,
            immediate_survival=immediate_survival,
            proliferation_survival=proliferation_survival,
        )
        for fraction_day in schedule.fraction_days
    )

    return Stage8RadiotherapyEvents(
        events=events,
        spatial_dose=spatial,
        proliferation_survival=proliferation_survival,
        dose_normalization=normalization,
    )
