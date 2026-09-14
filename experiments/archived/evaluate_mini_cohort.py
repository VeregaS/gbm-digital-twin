import argparse
from concurrent.futures import (
    ProcessPoolExecutor,
    as_completed,
)
from pathlib import Path

import pandas as pd

from gbm_twin.data.cfb_metadata import (
    CFBMetadata,
)
from gbm_twin.evaluation.cohort import (
    RAW_RESULT_COLUMNS,
    EvaluationConfig,
    evaluate_patient,
)
from gbm_twin.evaluation.config import (
    evaluation_signature,
    load_cohort_experiment_config,
)

DEFAULT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run expensive GBM cohort evaluation."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--patients",
        type=int,
        nargs="*",
        default=None,
        help=(
            "Evaluate only selected patient IDs."
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Number of parallel patient workers."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Recompute selected patients even "
            "when valid cached results exist."
        ),
    )

    parser.add_argument(
        "--adopt-legacy-cache",
        action="store_true",
        help=(
            "Trust an existing raw CSV without "
            "an evaluation signature and mark it "
            "as produced by the current config."
        ),
    )

    return parser.parse_args()


def evaluate_worker(
    patient_id: int,
    metadata_root: str,
    patients_root: str,
    config: EvaluationConfig,
) -> dict[str, float | int]:
    metadata = CFBMetadata(
        Path(metadata_root)
    )

    return evaluate_patient(
        patient_id,
        metadata,
        Path(patients_root),
        config,
    )


def load_cache(
    path: Path,
    *,
    signature: str,
    valid_patient_ids: tuple[int, ...],
    adopt_legacy_cache: bool,
) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()

    dataframe = pd.read_csv(
        path
    )

    if "patient_id" not in dataframe.columns:
        raise ValueError(
            "Existing raw CSV does not contain "
            "'patient_id'"
        )

    if (
        "evaluation_signature"
        not in dataframe.columns
    ):
        if not adopt_legacy_cache:
            print()
            print(
                "Legacy raw CSV found without "
                "evaluation signature."
            )
            print(
                "It will not be reused unless "
                "--adopt-legacy-cache is supplied."
            )

            return pd.DataFrame()

        print()
        print(
            "Adopting existing legacy raw CSV "
            "as cache for the current "
            "evaluation configuration."
        )

        dataframe[
            "evaluation_signature"
        ] = signature

    if (
        "predicted_volume_t2_cm3"
        not in dataframe.columns
    ):
        legacy_columns = {
            "volume_t0_cm3",
            "volume_t1_cm3",
            "dt01",
            "dt12",
        }

        if legacy_columns.issubset(
            dataframe.columns
        ):
            print(
                "Reconstructing legacy "
                "predicted_volume_t2_cm3."
            )

            growth_factor = (
                dataframe["volume_t1_cm3"]
                / dataframe["volume_t0_cm3"]
            ) ** (
                dataframe["dt12"]
                / dataframe["dt01"]
            )

            dataframe[
                "predicted_volume_t2_cm3"
            ] = (
                dataframe["volume_t1_cm3"]
                * growth_factor
            )
    
    dataframe = dataframe[
        dataframe[
            "evaluation_signature"
        ].astype(str)
        == signature
    ].copy()

    dataframe = dataframe[
        dataframe["patient_id"].isin(
            valid_patient_ids
        )
    ].copy()

    available_columns = [
        column
        for column in RAW_RESULT_COLUMNS
        if column in dataframe.columns
    ]

    required_columns = set(
        RAW_RESULT_COLUMNS
    )

    missing_columns = (
        required_columns
        - set(available_columns)
    )

    if missing_columns:
        names = ", ".join(
            sorted(missing_columns)
        )

        print()
        print(
            "Existing cache is missing raw "
            f"columns: {names}"
        )
        print(
            "Cache will not be reused."
        )

        return pd.DataFrame()

    return dataframe[
        [
            *RAW_RESULT_COLUMNS,
            "evaluation_signature",
        ]
    ].copy()


def merge_result(
    dataframe: pd.DataFrame,
    result: dict[str, float | int],
    *,
    signature: str,
) -> pd.DataFrame:
    row = {
        **result,
        "evaluation_signature": signature,
    }

    if dataframe.empty:
        merged = pd.DataFrame(
            [row]
        )
    else:
        filtered = dataframe[
            dataframe["patient_id"]
            != result["patient_id"]
        ].copy()

        merged = pd.concat(
            [
                filtered,
                pd.DataFrame([row]),
            ],
            ignore_index=True,
        )

    return merged.sort_values(
        "patient_id"
    ).reset_index(
        drop=True
    )


def save_cache(
    dataframe: pd.DataFrame,
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        path,
        index=False,
    )


def resolve_patient_ids(
    configured_patient_ids: tuple[int, ...],
    requested_patient_ids: list[int] | None,
) -> list[int]:
    if requested_patient_ids is None:
        return list(
            configured_patient_ids
        )

    configured = set(
        configured_patient_ids
    )

    invalid = [
        patient_id
        for patient_id
        in requested_patient_ids
        if patient_id not in configured
    ]

    if invalid:
        raise ValueError(
            "Requested patients are not in "
            f"the experiment config: {invalid}"
        )

    return list(
        dict.fromkeys(
            requested_patient_ids
        )
    )


def main() -> None:
    args = parse_args()

    if args.workers < 1:
        raise ValueError(
            "--workers must be at least 1"
        )

    experiment = (
        load_cohort_experiment_config(
            args.config
        )
    )

    signature = evaluation_signature(
        experiment.evaluation
    )

    selected_patient_ids = (
        resolve_patient_ids(
            experiment.patient_ids,
            args.patients,
        )
    )

    cache = load_cache(
        experiment.raw_output_csv,
        signature=signature,
        valid_patient_ids=(
            experiment.patient_ids
        ),
        adopt_legacy_cache=(
            args.adopt_legacy_cache
        ),
    )

    if args.force:
        cached_patient_ids: set[int] = set()
    else:
        cached_patient_ids = {
            int(patient_id)
            for patient_id
            in cache.get(
                "patient_id",
                pd.Series(
                    dtype=int
                ),
            ).tolist()
        }

    patients_to_evaluate = [
        patient_id
        for patient_id
        in selected_patient_ids
        if patient_id
        not in cached_patient_ids
    ]

    patients_from_cache = [
        patient_id
        for patient_id
        in selected_patient_ids
        if patient_id
        in cached_patient_ids
    ]

    print()
    print(
        f"Evaluation signature: {signature}"
    )

    print(
        "Selected patients:",
        selected_patient_ids,
    )

    print(
        "Cached:",
        patients_from_cache,
    )

    print(
        "Need PDE evaluation:",
        patients_to_evaluate,
    )

    if not patients_to_evaluate:
        save_cache(
            cache,
            experiment.raw_output_csv,
        )

        print()
        print(
            "No PDE simulations needed."
        )

        print(
            f"Raw results: "
            f"{experiment.raw_output_csv}"
        )

        return

    if args.workers == 1:
        metadata = CFBMetadata(
            experiment.metadata_root
        )

        for patient_id in patients_to_evaluate:
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

            cache = merge_result(
                cache,
                result,
                signature=signature,
            )

            save_cache(
                cache,
                experiment.raw_output_csv,
            )

            print(
                f"Saved patient {patient_id}"
            )

    else:
        print()
        print(
            f"Running with {args.workers} "
            "parallel patient workers."
        )

        with ProcessPoolExecutor(
            max_workers=args.workers
        ) as executor:
            future_to_patient = {
                executor.submit(
                    evaluate_worker,
                    patient_id,
                    str(
                        experiment.metadata_root
                    ),
                    str(
                        experiment.patients_root
                    ),
                    experiment.evaluation,
                ): patient_id
                for patient_id
                in patients_to_evaluate
            }

            for future in as_completed(
                future_to_patient
            ):
                patient_id = (
                    future_to_patient[
                        future
                    ]
                )

                result = future.result()

                cache = merge_result(
                    cache,
                    result,
                    signature=signature,
                )

                save_cache(
                    cache,
                    experiment.raw_output_csv,
                )

                print()
                print(
                    f"Completed and saved "
                    f"patient {patient_id}"
                )

    print()
    print("=" * 60)
    print("RAW COHORT RESULTS")
    print("=" * 60)

    selected_results = cache[
        cache["patient_id"].isin(
            selected_patient_ids
        )
    ].copy()

    print(
        selected_results.to_string(
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
        f"Saved: {experiment.raw_output_csv}"
    )


if __name__ == "__main__":
    main()