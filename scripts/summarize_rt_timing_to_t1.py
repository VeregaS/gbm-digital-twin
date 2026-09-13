from pathlib import Path
from typing import Any, cast

import pandas as pd

from gbm_twin.models.rt_schedule import (
    reconstruct_weekday_like_schedule,
)

INPUT_PATH = Path(
    "results/prediction_cohort_treatment_summary.csv"
)

OUTPUT_PATH = Path(
    "results/prediction_cohort_rt_timing.csv"
)


def classify_t1_timing(
    *,
    dt01: float,
    first_fraction_day: float,
    last_fraction_day: float,
) -> str:
    if dt01 < first_fraction_day:
        return "before_rt"

    if dt01 < last_fraction_day:
        return "during_rt"

    return "after_rt"


def main() -> None:
    dataframe = pd.read_csv(
        INPUT_PATH
    )

    required_columns = {
        "patient_id",
        "dt01",
        "rt_start_day",
        "rt_dose_gy",
        "rt_fractions",
        "schedule_status",
    }

    missing = (
        required_columns
        - set(dataframe.columns)
    )

    if missing:
        names = ", ".join(
            sorted(missing)
        )

        raise ValueError(
            f"Missing columns: {names}"
        )

    records = cast(
        list[dict[str, Any]],
        dataframe.to_dict(
            orient="records"
        ),
    )

    timing_rows: list[
        dict[str, object]
    ] = []

    for row in records:
        patient_id = int(
            row["patient_id"]
        )

        if (
            row["schedule_status"]
            != "reconstructed"
        ):
            timing_rows.append(
                {
                    "patient_id": patient_id,
                    "t1_rt_timing": "unknown",
                    "fractions_by_t1": None,
                    "fraction_completion_t1": None,
                    "dose_by_t1_gy": None,
                    "rt_completed_by_t1": None,
                }
            )

            continue

        dt01 = float(
            row["dt01"]
        )

        start_day = float(
            row["rt_start_day"]
        )

        total_dose_gy = float(
            row["rt_dose_gy"]
        )

        fractions_number = int(
            float(
                row["rt_fractions"]
            )
        )

        schedule = (
            reconstruct_weekday_like_schedule(
                start_day=start_day,
                total_dose_gy=total_dose_gy,
                fractions_number=fractions_number,
            )
        )

        fractions_by_t1 = sum(
            fraction_day <= dt01
            for fraction_day
            in schedule.fraction_days
        )

        completion = (
            fractions_by_t1
            / schedule.fractions_number
        )

        dose_by_t1 = (
            fractions_by_t1
            * schedule.dose_per_fraction_gy
        )

        first_fraction_day = (
            schedule.fraction_days[0]
        )

        last_fraction_day = (
            schedule.fraction_days[-1]
        )

        timing = classify_t1_timing(
            dt01=dt01,
            first_fraction_day=(
                first_fraction_day
            ),
            last_fraction_day=(
                last_fraction_day
            ),
        )

        timing_rows.append(
            {
                "patient_id": patient_id,
                "t1_rt_timing": timing,
                "fractions_by_t1": (
                    fractions_by_t1
                ),
                "fraction_completion_t1": (
                    completion
                ),
                "dose_by_t1_gy": (
                    dose_by_t1
                ),
                "rt_completed_by_t1": (
                    fractions_by_t1
                    == schedule.fractions_number
                ),
            }
        )

    timing_frame = pd.DataFrame(
        timing_rows
    )

    result = dataframe.merge(
        timing_frame,
        on="patient_id",
        how="left",
        validate="one_to_one",
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print()
    print("=" * 60)
    print("RT TIMING RELATIVE TO T1")
    print("=" * 60)

    print()
    print("T1 timing:")

    print(
        result[
            "t1_rt_timing"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    reconstructed = result[
        result["schedule_status"]
        == "reconstructed"
    ]

    print()
    print("RT completed by t1:")

    print(
        reconstructed[
            "rt_completed_by_t1"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    incomplete = reconstructed[
        ~reconstructed[
            "rt_completed_by_t1"
        ].astype(bool)
    ]

    print()
    print(
        "Patients with incomplete RT at t1:",
        len(incomplete),
    )

    if not incomplete.empty:
        print()

        print(
            incomplete[
                [
                    "patient_id",
                    "dt01",
                    "rt_start_day",
                    "rt_dose_gy",
                    "rt_fractions",
                    "fractions_by_t1",
                    "fraction_completion_t1",
                    "dose_by_t1_gy",
                    "last_fraction_day",
                ]
            ].to_string(
                index=False,
                float_format=(
                    lambda value: (
                        f"{value:.4f}"
                    )
                ),
            )
        )

    print()
    print(
        "Fraction completion at t1:"
    )

    print(
        reconstructed[
            "fraction_completion_t1"
        ].describe().to_string()
    )

    print()
    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()