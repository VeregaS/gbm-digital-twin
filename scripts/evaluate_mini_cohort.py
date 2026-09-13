from pathlib import Path

import pandas as pd

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.evaluation.cohort import (
    evaluate_patient,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)


def main() -> None:
    config_path = Path(
        "configs/experiments/mini_cohort.yaml"
    )

    experiment = (
        load_cohort_experiment_config(
            config_path
        )
    )

    metadata = CFBMetadata(
        experiment.metadata_root
    )

    results: list[
        dict[str, float | int]
    ] = []

    for patient_id in experiment.patient_ids:
        print()
        print("=" * 60)
        print(
            f"PATIENT {patient_id}"
        )
        print("=" * 60)

        result = evaluate_patient(
            patient_id,
            metadata,
            experiment.patients_root,
            experiment.evaluation,
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

    experiment.output_csv.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        experiment.output_csv,
        index=False,
    )

    print()
    print(
        f"Saved: {experiment.output_csv}"
    )


if __name__ == "__main__":
    main()