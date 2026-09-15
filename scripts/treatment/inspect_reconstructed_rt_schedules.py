from pathlib import Path

import pandas as pd

from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)
from gbm_twin.models.rt_schedule import (
    reconstruct_weekday_like_schedule,
)

CONFIG_PATH = Path(
    "configs/experiments/mini_cohort.yaml"
)


def main() -> None:
    experiment = (
        load_cohort_experiment_config(
            CONFIG_PATH
        )
    )

    treatment_metadata = (
        CFBTreatmentMetadata(
            experiment.metadata_root
        )
    )

    rows: list[
        dict[str, object]
    ] = []

    for patient_id in experiment.patient_ids:
        treatment = (
            treatment_metadata.treatment(
                patient_id
            )
        )

        if treatment is None:
            rows.append(
                {
                    "patient_id": patient_id,
                    "status": "missing_record",
                }
            )

            continue

        start_day = (
            treatment.radiotherapy_start_day
        )

        dose_gy = treatment.dose_gy

        fractions = (
            treatment.fractions_number
        )

        if (
            start_day is None
            or dose_gy is None
            or fractions is None
        ):
            rows.append(
                {
                    "patient_id": patient_id,
                    "status": (
                        "insufficient_metadata"
                    ),
                }
            )

            continue

        schedule = (
            reconstruct_weekday_like_schedule(
                start_day=start_day,
                total_dose_gy=dose_gy,
                fractions_number=fractions,
            )
        )

        rows.append(
            {
                "patient_id": patient_id,
                "status": "reconstructed",
                "rt_start_day": (
                    schedule.start_day
                ),
                "total_dose_gy": (
                    schedule.total_dose_gy
                ),
                "fractions": (
                    schedule.fractions_number
                ),
                "dose_per_fraction_gy": (
                    schedule
                    .dose_per_fraction_gy
                ),
                "first_fraction_day": (
                    schedule.fraction_days[0]
                ),
                "last_fraction_day": (
                    schedule.fraction_days[-1]
                ),
                "assumption": (
                    schedule.assumption
                ),
            }
        )

    dataframe = pd.DataFrame(
        rows
    )

    print()
    print("=" * 60)
    print("RECONSTRUCTED RT SCHEDULES")
    print("=" * 60)

    print(
        dataframe.to_string(
            index=False,
            float_format=(
                lambda value: (
                    f"{value:.4f}"
                )
            ),
        )
    )


if __name__ == "__main__":
    main()