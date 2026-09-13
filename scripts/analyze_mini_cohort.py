import argparse
from pathlib import Path

import pandas as pd

from gbm_twin.evaluation.analysis import (
    analyze_results,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)

DEFAULT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze cached GBM cohort results "
            "without running PDE simulations."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    return parser.parse_args()


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    compatible = dataframe[
        dataframe[
            "calibration_compatible"
        ]
    ]

    print()
    print("=" * 60)
    print("COHORT SUMMARY")
    print("=" * 60)

    print(
        f"Patients: {len(dataframe)}"
    )

    print(
        "Calibration compatible:",
        int(
            dataframe[
                "calibration_compatible"
            ].sum()
        ),
    )

    print()
    print("Trajectory t0 -> t1:")
    print(
        dataframe[
            "trajectory_t0_t1"
        ].value_counts().to_string()
    )

    print()
    print("Trajectory t1 -> t2:")
    print(
        dataframe[
            "trajectory_t1_t2"
        ].value_counts().to_string()
    )

    print()
    print("All patients:")

    print(
        "  Mean Twin Dice:",
        round(
            float(
                dataframe[
                    "twin_dice"
                ].mean()
            ),
            4,
        ),
    )

    print(
        "  Mean Persistence Dice:",
        round(
            float(
                dataframe[
                    "persistence_dice"
                ].mean()
            ),
            4,
        ),
    )

    print(
        "  Mean Morphological Dice:",
        round(
            float(
                dataframe[
                    "morphological_dice"
                ].mean()
            ),
            4,
        ),
    )

    if not compatible.empty:
        print()
        print(
            "Calibration-compatible patients:"
        )

        print(
            "  Mean Twin Dice:",
            round(
                float(
                    compatible[
                        "twin_dice"
                    ].mean()
                ),
                4,
            ),
        )

        print(
            "  Mean Persistence Dice:",
            round(
                float(
                    compatible[
                        "persistence_dice"
                    ].mean()
                ),
                4,
            ),
        )

        print(
            "  Mean Morphological Dice:",
            round(
                float(
                    compatible[
                        "morphological_dice"
                    ].mean()
                ),
                4,
            ),
        )


def main() -> None:
    args = parse_args()

    experiment = (
        load_cohort_experiment_config(
            args.config
        )
    )

    if not experiment.raw_output_csv.is_file():
        raise FileNotFoundError(
            "Raw evaluation CSV not found: "
            f"{experiment.raw_output_csv}"
        )

    raw = pd.read_csv(
        experiment.raw_output_csv
    )

    analyzed = analyze_results(
        raw,
        stable_threshold=(
            experiment
            .trajectory_stable_threshold
        ),
    )

    experiment.analyzed_output_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    analyzed.to_csv(
        experiment.analyzed_output_csv,
        index=False,
    )

    display_columns = [
        "patient_id",
        "volume_t0_cm3",
        "volume_t1_cm3",
        "volume_t2_cm3",
        "volume_change_t0_t1",
        "trajectory_t0_t1",
        "volume_change_t1_t2",
        "trajectory_t1_t2",
        "calibration_compatible",
        "D",
        "rho",
        "twin_dice",
        "persistence_dice",
        "morphological_dice",
        "twin_minus_persistence_dice",
    ]

    print()
    print("=" * 60)
    print("ANALYZED COHORT")
    print("=" * 60)

    print(
        analyzed[
            display_columns
        ].to_string(
            index=False,
            float_format=(
                lambda value: (
                    f"{value:.4f}"
                )
            ),
        )
    )

    print_summary(
        analyzed
    )

    print()
    print(
        f"Saved: "
        f"{experiment.analyzed_output_csv}"
    )


if __name__ == "__main__":
    main()