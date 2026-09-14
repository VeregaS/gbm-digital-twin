import argparse
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from gbm_twin.data.cfb_metadata import (
    CFBMetadata,
)
from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)
from gbm_twin.evaluation.treatment_aware import (
    evaluate_treatment_aware_patient,
)

DEFAULT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)

DEFAULT_CACHE_DIR = Path(
    ".cache/gbm_twin/calibration"
)

DEFAULT_OUTPUT = Path(
    "results/mini_cohort_treatment_aware.csv"
)

ResultRow = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate treatment-aware Digital Twin "
            "on the mini cohort."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--alpha",
        type=float,
        default=0.10,
    )

    parser.add_argument(
        "--alpha-beta",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--patients",
        type=int,
        nargs="+",
        default=None,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Recompute patients already "
            "present in output CSV."
        ),
    )

    return parser.parse_args()


def load_configured_patients(
    config_path: Path,
) -> list[int]:
    with config_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = yaml.safe_load(
            file
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Experiment YAML root "
            "must be a mapping"
        )

    raw_patients = payload.get(
        "patients"
    )

    if not isinstance(
        raw_patients,
        list,
    ):
        raise ValueError(
            "Experiment YAML must contain "
            "a patients list"
        )

    patients: list[int] = []

    for value in raw_patients:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
        ):
            raise ValueError(
                "All patient IDs in YAML "
                "must be integers"
            )

        patients.append(
            value
        )

    if not patients:
        raise ValueError(
            "Patients list must not be empty"
        )

    return patients


def load_existing_results(
    output_path: Path,
) -> pd.DataFrame:
    if not output_path.exists():
        return pd.DataFrame()

    return pd.read_csv(
        output_path
    )


def dataframe_rows(
    dataframe: pd.DataFrame,
) -> list[ResultRow]:
    raw_records = dataframe.to_dict(
        orient="records"
    )

    return [
        {
            str(key): value
            for key, value
            in record.items()
        }
        for record in raw_records
    ]


def patient_id_from_row(
    row: ResultRow,
) -> int:
    value = row.get(
        "patient_id"
    )

    if isinstance(
        value,
        bool,
    ):
        raise ValueError(
            "Invalid boolean patient_id"
        )

    if isinstance(
        value,
        int,
    ):
        return value

    if isinstance(
        value,
        float,
    ):
        if not value.is_integer():
            raise ValueError(
                f"Invalid patient_id: {value}"
            )

        return int(
            value
        )

    if isinstance(
        value,
        str,
    ):
        return int(
            value
        )

    raise ValueError(
        f"Invalid patient_id value: {value!r}"
    )


def save_results(
    rows: list[ResultRow],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = pd.DataFrame(
        rows
    )

    dataframe = dataframe.sort_values(
        "patient_id"
    ).reset_index(
        drop=True
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )


def has_reconstructable_rt(
    treatment_metadata: CFBTreatmentMetadata,
    patient_id: int,
) -> bool:
    record = treatment_metadata.treatment(
        patient_id
    )

    if record is None:
        return False

    return (
        record.radiotherapy_start_day
        is not None
        and record.dose_gy is not None
        and record.fractions_number is not None
    )


def print_summary(
    dataframe: pd.DataFrame,
) -> None:
    if dataframe.empty:
        print()
        print(
            "No patients evaluated."
        )
        return

    twin_mean = float(
        dataframe[
            "prediction_dice"
        ].mean()
    )

    persistence_mean = float(
        dataframe[
            "persistence_dice"
        ].mean()
    )

    dice_difference = (
        dataframe["prediction_dice"]
        - dataframe["persistence_dice"]
    )

    wins = int(
        (
            dice_difference
            > 1e-12
        ).sum()
    )

    ties = int(
        (
            dice_difference.abs()
            <= 1e-12
        ).sum()
    )

    losses = (
        len(dataframe)
        - wins
        - ties
    )

    print()
    print("=" * 60)
    print(
        "MINI-COHORT SUMMARY"
    )
    print("=" * 60)

    print(
        "Patients evaluated: "
        f"{len(dataframe)}"
    )

    print(
        "Mean treatment-aware Dice: "
        f"{twin_mean:.4f}"
    )

    print(
        "Mean persistence Dice: "
        f"{persistence_mean:.4f}"
    )

    print(
        "Mean Dice difference: "
        f"{twin_mean - persistence_mean:+.4f}"
    )

    print(
        "Treatment-aware vs persistence: "
        f"{wins} wins / "
        f"{ties} ties / "
        f"{losses} losses"
    )

    columns = [
        "patient_id",
        "diffusion",
        "proliferation",
        "calibration_dice",
        "calibration_loss",
        "prediction_dice",
        "persistence_dice",
    ]

    print()

    print(
        dataframe[
            columns
        ].to_string(
            index=False,
            float_format=(
                lambda value: (
                    f"{value:.4f}"
                )
            ),
        )
    )


def main() -> None:
    args = parse_args()

    if args.alpha < 0:
        raise ValueError(
            "--alpha must be non-negative"
        )

    if args.alpha_beta <= 0:
        raise ValueError(
            "--alpha-beta must be positive"
        )

    if args.workers < 1:
        raise ValueError(
            "--workers must be at least 1"
        )

    experiment = (
        load_cohort_experiment_config(
            args.config
        )
    )

    metadata = CFBMetadata(
        experiment.metadata_root
    )

    treatment_metadata = (
        CFBTreatmentMetadata(
            experiment.metadata_root
        )
    )

    if args.patients is not None:
        patients = list(
            args.patients
        )
    else:
        patients = (
            load_configured_patients(
                args.config
            )
        )

    existing = load_existing_results(
        args.output
    )

    rows: list[ResultRow] = []

    completed: set[int] = set()

    if not existing.empty:
        rows = dataframe_rows(
            existing
        )

        completed = {
            patient_id_from_row(
                row
            )
            for row in rows
        }

    print()
    print("=" * 60)
    print(
        "TREATMENT-AWARE MINI COHORT"
    )
    print("=" * 60)

    print(
        "Patients requested: "
        f"{patients}"
    )

    print(
        f"alpha: "
        f"{args.alpha:.4f} /Gy"
    )

    print(
        f"alpha/beta: "
        f"{args.alpha_beta:.2f} Gy"
    )

    print(
        f"workers: "
        f"{args.workers}"
    )

    print(
        f"cache: "
        f"{DEFAULT_CACHE_DIR}"
    )

    for index, patient_id in enumerate(
        patients,
        start=1,
    ):
        print()
        print("=" * 60)

        print(
            f"PATIENT "
            f"{patient_id} "
            f"({index}/{len(patients)})"
        )

        print("=" * 60)

        if (
            patient_id in completed
            and not args.force
        ):
            print(
                "Already evaluated. "
                "Skipping."
            )

            continue

        if not has_reconstructable_rt(
            treatment_metadata,
            patient_id,
        ):
            print(
                "RT schedule cannot be "
                "reconstructed. Skipping."
            )

            continue

        result = (
            evaluate_treatment_aware_patient(
                patient_id,
                experiment=experiment,
                metadata=metadata,
                treatment_metadata=(
                    treatment_metadata
                ),
                alpha_per_gy=args.alpha,
                alpha_beta_ratio_gy=(
                    args.alpha_beta
                ),
                cache_dir=(
                    DEFAULT_CACHE_DIR
                ),
                workers=args.workers,
            )
        )

        row: ResultRow = asdict(
            result
        )

        if patient_id in completed:
            rows = [
                existing_row
                for existing_row in rows
                if patient_id_from_row(
                    existing_row
                )
                != patient_id
            ]

        rows.append(
            row
        )

        completed.add(
            patient_id
        )

        save_results(
            rows,
            args.output,
        )

        print()
        print(
            "Calibration:"
        )

        print(
            f"  D="
            f"{result.diffusion:.4f}"
        )

        print(
            "  rho="
            f"{result.proliferation:.4f}"
        )

        print(
            "  Dice="
            f"{result.calibration_dice:.4f}"
        )

        print(
            "  Loss="
            f"{result.calibration_loss:.4f}"
        )

        print(
            "Prediction:"
        )

        print(
            "  Twin Dice="
            f"{result.prediction_dice:.4f}"
        )

        print(
            "  Persistence Dice="
            f"{result.persistence_dice:.4f}"
        )

        print(
            "  Delta="
            f"{result.prediction_dice - result.persistence_dice:+.4f}"
        )

        print(
            "Saved checkpoint: "
            f"{args.output}"
        )

    final_dataframe = pd.DataFrame(
        rows
    )

    if not final_dataframe.empty:
        requested_set = set(
            patients
        )

        patient_ids = (
            final_dataframe[
                "patient_id"
            ]
            .astype(int)
        )

        final_dataframe = (
            final_dataframe[
                patient_ids.isin(
                    requested_set
                )
            ]
        )

    print_summary(
        final_dataframe
    )


if __name__ == "__main__":
    main()