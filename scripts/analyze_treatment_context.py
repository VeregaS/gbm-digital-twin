import argparse
from pathlib import Path
from typing import Any, cast

import pandas as pd

from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)

DEFAULT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)

DEFAULT_OUTPUT = Path(
    "results/mini_cohort_treatment.csv"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Join radiotherapy metadata with "
            "cached cohort analysis."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def classify_calibration_rt_status(
    *,
    rt_start_day: float | None,
    dt01_days: float,
) -> str:
    if rt_start_day is None:
        return "unknown"

    if rt_start_day <= dt01_days:
        return "exposed"

    return "unexposed"


def classify_prediction_rt_status(
    *,
    rt_start_day: float | None,
    dt01_days: float,
    dt12_days: float,
) -> str:
    if rt_start_day is None:
        return "unknown"

    prediction_end_day = (
        dt01_days + dt12_days
    )

    if rt_start_day <= prediction_end_day:
        return "exposed_or_post_rt"

    return "unexposed"


def has_segmentation_provenance_change(
    gtv_type_t0: str | None,
    gtv_type_t1: str | None,
) -> bool | None:
    if (
        gtv_type_t0 is None
        or gtv_type_t1 is None
    ):
        return None

    return gtv_type_t0 != gtv_type_t1


def main() -> None:
    args = parse_args()

    experiment = (
        load_cohort_experiment_config(
            args.config
        )
    )

    if not (
        experiment
        .analyzed_output_csv
        .is_file()
    ):
        raise FileNotFoundError(
            "Analyzed cohort CSV not found: "
            f"{experiment.analyzed_output_csv}"
        )

    dataframe = pd.read_csv(
        experiment.analyzed_output_csv
    )

    required_columns = {
        "patient_id",
        "dt01",
        "dt12",
        "trajectory_t0_t1",
        "trajectory_t1_t2",
        "calibration_compatible",
        "twin_dice",
        "persistence_dice",
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
            "Analyzed cohort CSV is missing "
            f"columns: {names}"
        )

    treatment_metadata = (
        CFBTreatmentMetadata(
            experiment.metadata_root
        )
    )

    treatment_rows: list[
        dict[str, object]
    ] = []

    patient_rows = cast(
        list[dict[str, Any]],
        dataframe[
            [
                "patient_id",
                "dt01",
                "dt12",
            ]
        ].to_dict(
            orient="records"
        ),
    )

    for row in patient_rows:
        patient_id = int(
            row["patient_id"]
        )

        dt01 = float(
            row["dt01"]
        )

        dt12 = float(
            row["dt12"]
        )

        context = (
            treatment_metadata.patient_context(
                patient_id,
                dt01_days=dt01,
                dt12_days=dt12,
            )
        )

        calibration_rt_status = (
            classify_calibration_rt_status(
                rt_start_day=(
                    context.rt_start_day
                ),
                dt01_days=dt01,
            )
        )

        prediction_rt_status = (
            classify_prediction_rt_status(
                rt_start_day=(
                    context.rt_start_day
                ),
                dt01_days=dt01,
                dt12_days=dt12,
            )
        )

        segmentation_change_t0_t1 = (
            has_segmentation_provenance_change(
                context.gtv_type_t0,
                context.gtv_type_t1,
            )
        )

        untreated_calibration_eligible = (
            calibration_rt_status
            == "unexposed"
        )

        treatment_rows.append(
            {
                "patient_id": patient_id,
                "has_treatment_record": (
                    context
                    .has_treatment_record
                ),
                "rt_start_day": (
                    context.rt_start_day
                ),
                "rt_start_phase": (
                    context.rt_start_phase
                ),
                "rt_started_by_t1": (
                    context.rt_started_by_t1
                ),
                "rt_started_by_t2": (
                    context.rt_started_by_t2
                ),
                "rt_dose_gy": (
                    context.rt_dose_gy
                ),
                "rt_fractions": (
                    context.rt_fractions
                ),
                "calibration_rt_status": (
                    calibration_rt_status
                ),
                "prediction_rt_status": (
                    prediction_rt_status
                ),
                "untreated_calibration_eligible": (
                    untreated_calibration_eligible
                ),
                "rtdose_t0_available": (
                    context
                    .rtdose_t0_available
                ),
                "rtdose_t1_available": (
                    context
                    .rtdose_t1_available
                ),
                "rtdose_t2_available": (
                    context
                    .rtdose_t2_available
                ),
                "gtv_type_t0": (
                    context.gtv_type_t0
                ),
                "gtv_type_t1": (
                    context.gtv_type_t1
                ),
                "gtv_type_t2": (
                    context.gtv_type_t2
                ),
                "segmentation_change_t0_t1": (
                    segmentation_change_t0_t1
                ),
            }
        )

    treatment_frame = pd.DataFrame(
        treatment_rows
    )

    result = dataframe.merge(
        treatment_frame,
        on="patient_id",
        how="left",
        validate="one_to_one",
    )

    result[
        "twin_minus_persistence_dice"
    ] = (
        result["twin_dice"]
        - result["persistence_dice"]
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        args.output,
        index=False,
    )

    display_columns = [
        "patient_id",
        "trajectory_t0_t1",
        "trajectory_t1_t2",
        "calibration_rt_status",
        "prediction_rt_status",
        "untreated_calibration_eligible",
        "rt_start_day",
        "rt_dose_gy",
        "rt_fractions",
        "gtv_type_t0",
        "gtv_type_t1",
        "segmentation_change_t0_t1",
        "twin_dice",
        "persistence_dice",
        "twin_minus_persistence_dice",
    ]

    print()
    print("=" * 60)
    print("TREATMENT CONTEXT")
    print("=" * 60)

    print(
        result[
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

    print()
    print("=" * 60)
    print("TREATMENT SUMMARY")
    print("=" * 60)

    print()
    print(
        "Calibration RT status:"
    )

    print(
        result[
            "calibration_rt_status"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    print()
    print(
        "Untreated calibration eligible:"
    )

    print(
        result[
            "untreated_calibration_eligible"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    print()
    print(
        "Segmentation provenance "
        "change t0 -> t1:"
    )

    print(
        result[
            "segmentation_change_t0_t1"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    print()
    print(
        f"Saved: {args.output}"
    )


if __name__ == "__main__":
    main()