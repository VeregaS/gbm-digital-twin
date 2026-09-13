from typing import cast

import pandas as pd

REQUIRED_COLUMNS = {
    "patient_id",
    "volume_t0_cm3",
    "volume_t1_cm3",
    "volume_t2_cm3",
    "twin_dice",
    "twin_volume_error",
    "persistence_dice",
    "persistence_volume_error",
    "morphological_dice",
    "morphological_volume_error",
}


def classify_volume_trajectory(
    relative_volume_change: float,
    *,
    stable_threshold: float,
) -> str:
    if stable_threshold < 0:
        raise ValueError(
            "Stable threshold must be non-negative"
        )

    if relative_volume_change > stable_threshold:
        return "growth"

    if relative_volume_change < -stable_threshold:
        return "regression"

    return "stable"


def analyze_results(
    dataframe: pd.DataFrame,
    *,
    stable_threshold: float,
) -> pd.DataFrame:
    if stable_threshold < 0:
        raise ValueError(
            "Stable threshold must be non-negative"
        )

    missing_columns = (
        REQUIRED_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        names = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing required columns: {names}"
        )

    result = dataframe.copy()

    volume_columns = [
        "volume_t0_cm3",
        "volume_t1_cm3",
        "volume_t2_cm3",
    ]
    if result[volume_columns].isna().any().any():
        raise ValueError(
            "Observed volumes must not contain missing values"
        )
    if (
        result[volume_columns]
        <= 0
    ).any().any():
        raise ValueError(
            "Observed volumes must be positive"
        )

    result["volume_change_t0_t1"] = (
        result["volume_t1_cm3"]
        - result["volume_t0_cm3"]
    ) / result["volume_t0_cm3"]

    result["volume_change_t1_t2"] = (
        result["volume_t2_cm3"]
        - result["volume_t1_cm3"]
    ) / result["volume_t1_cm3"]

    result["trajectory_t0_t1"] = (
        result["volume_change_t0_t1"].map(
            lambda value: (
                classify_volume_trajectory(
                    cast(float, value),
                    stable_threshold=(
                        stable_threshold
                    ),
                )
            )
        )
    )

    result["trajectory_t1_t2"] = (
        result["volume_change_t1_t2"].map(
            lambda value: (
                classify_volume_trajectory(
                    cast(float, value),
                    stable_threshold=(
                        stable_threshold
                    ),
                )
            )
        )
    )

    result["calibration_compatible"] = (
        result["trajectory_t0_t1"]
        != "regression"
    )

    result["twin_minus_persistence_dice"] = (
        result["twin_dice"]
        - result["persistence_dice"]
    )

    result["twin_beats_persistence"] = (
        result["twin_dice"]
        > result["persistence_dice"]
    )

    return result