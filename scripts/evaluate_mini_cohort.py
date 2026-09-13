from pathlib import Path

import pandas as pd

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.evaluation.cohort import (
    EvaluationConfig,
    evaluate_patient,
)


def main() -> None:
    metadata = CFBMetadata(
        Path(
            r"D:\Datasets\CFB-GBM\metadata"
        )
    )

    patients_root = Path(
        r"D:\Datasets\CFB-GBM\patients"
    )

    config = EvaluationConfig()

    patient_ids = [
        8,
        18,
        42,
    ]

    results: list[
        dict[str, float | int]
    ] = []

    for patient_id in patient_ids:
        print()
        print("=" * 60)
        print(
            f"PATIENT {patient_id}"
        )
        print("=" * 60)

        result = evaluate_patient(
            patient_id,
            metadata,
            patients_root,
            config,
        )

        results.append(
            result
        )

    dataframe = pd.DataFrame(
        results
    )

    print()
    print("=" * 60)
    print("MINI COHORT RESULTS")
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

    output_dir = Path(
        "results"
    )

    output_dir.mkdir(
        exist_ok=True
    )

    output_path = (
        output_dir
        / "mini_cohort.csv"
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()