from pathlib import Path

import pandas as pd

INPUT_PATH = Path(
    "results/prediction_cohort_rt_timing.csv"
)


def classify_post_rt_gap(
    days: float,
) -> str:
    if days < 0:
        return "invalid"

    if days <= 7:
        return "0-7 days"

    if days <= 30:
        return "8-30 days"

    if days <= 60:
        return "31-60 days"

    return ">60 days"


def main() -> None:
    dataframe = pd.read_csv(
        INPUT_PATH
    )

    reconstructed = dataframe[
        dataframe["schedule_status"]
        == "reconstructed"
    ].copy()

    reconstructed[
        "post_rt_gap_days"
    ] = (
        reconstructed["dt01"]
        - reconstructed["last_fraction_day"]
    )

    if (
        reconstructed[
            "post_rt_gap_days"
        ]
        < 0
    ).any():
        raise ValueError(
            "Found t1 before reconstructed "
            "RT completion"
        )

    reconstructed[
        "post_rt_gap_group"
    ] = reconstructed[
        "post_rt_gap_days"
    ].map(
        classify_post_rt_gap
    )

    print()
    print("=" * 60)
    print("POST-RT GAP TO T1")
    print("=" * 60)

    print()
    print(
        reconstructed[
            "post_rt_gap_days"
        ].describe().to_string()
    )

    print()
    print("Gap groups:")

    order = [
        "0-7 days",
        "8-30 days",
        "31-60 days",
        ">60 days",
    ]

    counts = (
        reconstructed[
            "post_rt_gap_group"
        ]
        .value_counts()
        .reindex(
            order,
            fill_value=0,
        )
    )

    print(
        counts.to_string()
    )

    print()
    print("Shortest gaps:")

    print(
        reconstructed[
            [
                "patient_id",
                "dt01",
                "last_fraction_day",
                "post_rt_gap_days",
            ]
        ]
        .sort_values(
            "post_rt_gap_days"
        )
        .head(10)
        .to_string(
            index=False
        )
    )

    print()
    print("Longest gaps:")

    print(
        reconstructed[
            [
                "patient_id",
                "dt01",
                "last_fraction_day",
                "post_rt_gap_days",
            ]
        ]
        .sort_values(
            "post_rt_gap_days",
            ascending=False,
        )
        .head(10)
        .to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()