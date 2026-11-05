from __future__ import annotations

from dataclasses import dataclass

from gbm_twin.data.cfb_treatment import TreatmentRecord
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.rt_schedule import (
    ReconstructedRadiotherapySchedule,
    build_pirt_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.treatment import (
    PIRTFractionatedRadiotherapy,
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
)


@dataclass(frozen=True)
class PostRadiotherapyConfig:
    initial_kill_rate_per_day: float
    decay_time_days: float

    def __post_init__(self) -> None:
        if self.initial_kill_rate_per_day <= 0.0:
            raise ValueError(
                "Post-RT initial kill rate must be positive"
            )

        if self.decay_time_days <= 0.0:
            raise ValueError(
                "Post-RT decay time must be positive"
            )


@dataclass(frozen=True)
class ReconstructedPatientTreatment:
    schedule: ReconstructedRadiotherapySchedule
    model: (
        PIRTFractionatedRadiotherapy
        | RadiotherapyProtocol
    )


def reconstruct_patient_treatment(
    record: TreatmentRecord,
    *,
    radiobiology: RadiobiologyParameters,
    post_rt: PostRadiotherapyConfig | None = None,
) -> ReconstructedPatientTreatment:
    start_day = record.radiotherapy_start_day
    total_dose_gy = record.dose_gy
    fractions_number = record.fractions_number

    if (
        start_day is None
        or total_dose_gy is None
        or fractions_number is None
    ):
        raise ValueError(
            f"Patient {record.patient_id}: "
            "radiotherapy schedule is incomplete"
        )

    schedule = reconstruct_weekday_like_schedule(
        start_day=start_day,
        total_dose_gy=total_dose_gy,
        fractions_number=fractions_number,
    )

    fractions = build_pirt_radiotherapy(
        schedule,
        radiobiology,
    )

    if post_rt is None:
        return ReconstructedPatientTreatment(
            schedule=schedule,
            model=fractions,
        )

    last_fraction_day = (
        schedule.fraction_days[-1]
    )

    effect = PostRadiotherapyEffect(
        start_day=last_fraction_day,
        initial_kill_rate=(
            post_rt.initial_kill_rate_per_day
        ),
        decay_time_days=(
            post_rt.decay_time_days
        ),
    )

    return ReconstructedPatientTreatment(
        schedule=schedule,
        model=RadiotherapyProtocol(
            fractions=fractions,
            post_effect=effect,
        ),
    )
