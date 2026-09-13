from pathlib import Path

import pandas as pd

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.models.rt_schedule import reconstruct_weekday_like_schedule


METADATA_ROOT = Path(
    r"D:\Datasets\CFB-GBM\metadata"
)

OUTPUT_PATH = Path(
    "results/prediction_cohort_treatment_summary.csv"
)


def classify_rt_status(
    *,
    rt_start_day: float | None,
    interval_end_day: float,
) -> str:
    if rt_start_day is None:
        return "unknown"

    if rt_start_day <= interval_end_day:
        return "exposed"

    return "unexposed"


def main() -> None:
    metadata = CFBMetadata(
        METADATA_ROOT
    )

    treatment_metadata = CFBTreatmentMetadata(
        METADATA_ROOT
    )

    patient_ids = metadata.prediction_cohort()

    rows: list[dict[str, object]] = []

    for patient_id in patient_ids:
        patient = metadata.patient(
            patient_id
        )

        dt01 = patient.interval_days(
            "t0",
            "t1",
        )

        dt12 = patient.interval_days(
            "t1",
            "t2",
        )

        context = (
            treatment_metadata.patient_context(
                patient_id,
                dt01_days=float(dt01),
                dt12_days=float(dt12),
            )
        )

        calibration_rt_status = (
            classify_rt_status(
                rt_start_day=(
                    context.rt_start_day
                ),
                interval_end_day=float(dt01),
            )
        )

        prediction_rt_status = (
            classify_rt_status(
                rt_start_day=(
                    context.rt_start_day
                ),
                interval_end_day=float(
                    dt01 + dt12
                ),
            )
        )

        schedule_status = (
            "unavailable"
        )

        dose_per_fraction_gy: (
            float | None
        ) = None

        last_fraction_day: (
            float | None
        ) = None

        treatment = (
            treatment_metadata.treatment(
                patient_id
            )
        )

        if treatment is not None:
            rt_start_day = (
                treatment
                .radiotherapy_start_day
            )

            dose_gy = treatment.dose_gy

            fractions = (
                treatment.fractions_number
            )

            if (
                rt_start_day is not None
                and dose_gy is not None
                and fractions is not None
            ):
                schedule = (
                    reconstruct_weekday_like_schedule(
                        start_day=(
                            rt_start_day
                        ),
                        total_dose_gy=(
                            dose_gy
                        ),
                        fractions_number=(
                            fractions
                        ),
                    )
                )

                schedule_status = (
                    "reconstructed"
                )

                dose_per_fraction_gy = (
                    schedule
                    .dose_per_fraction_gy
                )

                last_fraction_day = (
                    schedule
                    .fraction_days[-1]
                )

        segmentation_change_t0_t1 = (
            None
        )

        if (
            context.gtv_type_t0
            is not None
            and context.gtv_type_t1
            is not None
        ):
            segmentation_change_t0_t1 = (
                context.gtv_type_t0
                != context.gtv_type_t1
            )

        rows.append(
            {
                "patient_id": patient_id,
                "dt01": dt01,
                "dt12": dt12,
                "calibration_rt_status": (
                    calibration_rt_status
                ),
                "prediction_rt_status": (
                    prediction_rt_status
                ),
                "rt_start_day": (
                    context.rt_start_day
                ),
                "rt_dose_gy": (
                    context.rt_dose_gy
                ),
                "rt_fractions": (
                    context.rt_fractions
                ),
                "schedule_status": (
                    schedule_status
                ),
                "dose_per_fraction_gy": (
                    dose_per_fraction_gy
                ),
                "last_fraction_day": (
                    last_fraction_day
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

    dataframe = pd.DataFrame(
        rows
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_PATH,
        index=False,
    )

    print()
    print("=" * 60)
    print("PREDICTION COHORT TREATMENT AUDIT")
    print("=" * 60)

    print(
        f"Patients: {len(dataframe)}"
    )

    print()
    print("Calibration RT status:")

    print(
        dataframe[
            "calibration_rt_status"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    print()
    print("Prediction RT status:")

    print(
        dataframe[
            "prediction_rt_status"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    print()
    print("Reconstructed schedules:")

    print(
        dataframe[
            "schedule_status"
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
        dataframe[
            "segmentation_change_t0_t1"
        ].value_counts(
            dropna=False
        ).to_string()
    )

    known_unexposed = dataframe[
        dataframe[
            "calibration_rt_status"
        ]
        == "unexposed"
    ]

    print()
    print(
        "Known unexposed calibration patients:",
        len(known_unexposed),
    )

    if not known_unexposed.empty:
        print(
            known_unexposed[
                [
                    "patient_id",
                    "dt01",
                    "rt_start_day",
                    "gtv_type_t0",
                    "gtv_type_t1",
                ]
            ].to_string(
                index=False
            )
        )

    print()
    print(
        f"Saved: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()