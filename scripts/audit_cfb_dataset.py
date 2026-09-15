from __future__ import annotations

import argparse
import os
from pathlib import Path

from gbm_twin.data.dataset_manifest import (
    DatasetAuditResult,
    audit_cfb_dataset,
    load_cfb_dataset_manifest,
    load_experiment_patient_ids,
)

REPOSITORY_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

DEFAULT_MANIFEST = (
    REPOSITORY_ROOT
    / "configs"
    / "datasets"
    / "cfb_gbm_v4.yaml"
)

DEFAULT_EXPERIMENT_CONFIG = (
    REPOSITORY_ROOT
    / "configs"
    / "experiments"
    / "mini_cohort.yaml"
)


def _path_from_argument_or_env(
    value: Path | None,
    environment_name: str,
) -> Path | None:
    if value is not None:
        return value

    environment_value = os.getenv(
        environment_name
    )

    if not environment_value:
        return None

    return Path(
        environment_value
    )


def _print_result(
    result: DatasetAuditResult,
    *,
    experiment_config: Path,
) -> None:
    manifest = result.manifest

    print(
        "CFB-GBM DATASET AUDIT"
    )
    print("=" * 60)

    print(
        "Pinned release : "
        f"{manifest.name} "
        f"Version {manifest.version}"
    )

    print(
        "Updated        : "
        f"{manifest.updated}"
    )

    print(
        "DOI            : "
        f"{manifest.doi}"
    )

    print(
        "Experiment     : "
        f"{experiment_config}"
    )

    print(
        "Metadata root  : "
        f"{result.metadata_root}"
    )

    print(
        "Patients root  : "
        f"{result.patients_root}"
    )

    print()

    if result.metadata_files:
        print(
            "Metadata files:"
        )

        for path in (
            result.metadata_files
        ):
            print(
                f"  [OK] {path.name}"
            )

        print()

    if (
        result.metadata_patient_count
        is not None
    ):
        print(
            "Metadata subjects     : "
            f"{result.metadata_patient_count}"
            "/"
            f"{manifest.expected_subjects}"
        )

    if (
        result.prediction_candidate_count
        is not None
    ):
        print(
            "Prediction candidates : "
            f"{result.prediction_candidate_count}"
        )

    print(
        "Experiment patients    : "
        f"{len(result.selected_patient_ids)}"
    )

    print(
        "Prepared patients check: "
        f"{result.checked_patient_count}"
    )

    if result.selected_patient_ids:
        selected_text = ", ".join(
            str(patient_id)
            for patient_id in (
                result.selected_patient_ids
            )
        )

        print(
            "Selected patient IDs  : "
            f"{selected_text}"
        )

    print()

    if (
        result.invalid_selected_patient_ids
    ):
        invalid_text = ", ".join(
            str(patient_id)
            for patient_id in (
                result.invalid_selected_patient_ids
            )
        )

        print(
            "Invalid experiment "
            "patients:"
        )

        print(
            f"  {invalid_text}"
        )

        print()

    if result.missing_patient_files:
        print(
            "Missing patient files "
            "(first 20):"
        )

        for path in (
            result.missing_patient_files[
                :20
            ]
        ):
            print(
                f"  [MISSING] {path}"
            )

        remaining = (
            len(
                result.missing_patient_files
            )
            - 20
        )

        if remaining > 0:
            print(
                f"  ... and "
                f"{remaining} more"
            )

        print()

    if result.passed:
        print(
            "RESULT: PASS"
        )

        print(
            "The pinned dataset metadata "
            "and the selected experiment "
            "cohort satisfy the MVP "
            "structural contract."
        )

        print(
            "NOTE: unselected prediction "
            "candidates do not need to be "
            "materialized in patients/."
        )

        print(
            "NOTE: this is a structural "
            "audit, not a cryptographic "
            "proof of the TCIA release."
        )

        return

    print(
        "RESULT: FAIL"
    )

    for issue in result.issues:
        print(
            f"  - {issue}"
        )


def build_parser() -> (
    argparse.ArgumentParser
):
    parser = argparse.ArgumentParser(
        description=(
            "Audit a local CFB-GBM "
            "checkout and the selected "
            "experiment cohort against "
            "the pinned MVP data contract."
        )
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=(
            "Dataset manifest. "
            f"Default: {DEFAULT_MANIFEST}"
        ),
    )

    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=(
            DEFAULT_EXPERIMENT_CONFIG
        ),
        help=(
            "Experiment configuration "
            "containing the patient list. "
            "Default: "
            f"{DEFAULT_EXPERIMENT_CONFIG}"
        ),
    )

    parser.add_argument(
        "--metadata-root",
        type=Path,
        help=(
            "CFB metadata directory. "
            "Falls back to "
            "GBM_TWIN_CFB_METADATA_ROOT."
        ),
    )

    parser.add_argument(
        "--patients-root",
        type=Path,
        help=(
            "Prepared patient directory. "
            "Falls back to "
            "GBM_TWIN_CFB_PATIENTS_ROOT."
        ),
    )

    return parser


def main() -> int:
    parser = build_parser()

    arguments = (
        parser.parse_args()
    )

    metadata_root = (
        _path_from_argument_or_env(
            arguments.metadata_root,
            "GBM_TWIN_CFB_METADATA_ROOT",
        )
    )

    patients_root = (
        _path_from_argument_or_env(
            arguments.patients_root,
            "GBM_TWIN_CFB_PATIENTS_ROOT",
        )
    )

    if metadata_root is None:
        parser.error(
            "Provide --metadata-root "
            "or set "
            "GBM_TWIN_CFB_METADATA_ROOT."
        )

    if patients_root is None:
        parser.error(
            "Provide --patients-root "
            "or set "
            "GBM_TWIN_CFB_PATIENTS_ROOT."
        )

    manifest = (
        load_cfb_dataset_manifest(
            arguments.manifest
        )
    )

    selected_patient_ids = (
        load_experiment_patient_ids(
            arguments.experiment_config
        )
    )

    result = audit_cfb_dataset(
        manifest,
        metadata_root=metadata_root,
        patients_root=patients_root,
        selected_patient_ids=(
            selected_patient_ids
        ),
    )

    _print_result(
        result,
        experiment_config=(
            arguments.experiment_config
            .resolve()
        ),
    )

    return (
        0
        if result.passed
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )