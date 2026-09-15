from __future__ import annotations

import argparse
import os
from pathlib import Path

from gbm_twin.workflows.anatomy_registration import (
    prepare_patient_registered_atlas,
)


def _environment_path(
    name: str,
) -> Path | None:
    value = os.getenv(
        name
    )

    if value is None:
        return None

    normalized = (
        value.strip()
    )

    if not normalized:
        return None

    return Path(
        normalized
    )


def _required_path(
    parser: argparse.ArgumentParser,
    value: Path | None,
    *,
    argument_name: str,
    environment_name: str,
) -> Path:
    if value is None:
        parser.error(
            f"{argument_name} is "
            "required, or set "
            f"{environment_name}"
        )

    return value.resolve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Register the anatomical "
            "atlas into one patient "
            "timepoint."
        )
    )

    parser.add_argument(
        "--patient-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--timepoint",
        choices=(
            "t0",
            "t1",
            "t2",
        ),
        required=True,
    )

    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=(
            _environment_path(
                "GBM_TWIN_CFB_METADATA_ROOT"
            )
        ),
    )

    parser.add_argument(
        "--patients-root",
        type=Path,
        default=(
            _environment_path(
                "GBM_TWIN_CFB_PATIENTS_ROOT"
            )
        ),
    )

    parser.add_argument(
        "--atlas-root",
        type=Path,
        default=(
            _environment_path(
                "GBM_TWIN_ATLAS_ROOT"
            )
        ),
    )

    return parser


def main() -> None:
    parser = build_parser()

    args = parser.parse_args()

    metadata_root = (
        _required_path(
            parser,
            args.metadata_root,
            argument_name=(
                "--metadata-root"
            ),
            environment_name=(
                "GBM_TWIN_CFB_METADATA_ROOT"
            ),
        )
    )

    patients_root = (
        _required_path(
            parser,
            args.patients_root,
            argument_name=(
                "--patients-root"
            ),
            environment_name=(
                "GBM_TWIN_CFB_PATIENTS_ROOT"
            ),
        )
    )

    atlas_root = (
        _required_path(
            parser,
            args.atlas_root,
            argument_name=(
                "--atlas-root"
            ),
            environment_name=(
                "GBM_TWIN_ATLAS_ROOT"
            ),
        )
    )

    result = (
        prepare_patient_registered_atlas(
            metadata_root=(
                metadata_root
            ),
            patients_root=(
                patients_root
            ),
            atlas_root=(
                atlas_root
            ),
            patient_id=(
                args.patient_id
            ),
            timepoint_name=(
                args.timepoint
            ),
        )
    )

    quality = (
        result.quality
    )

    print()
    print(
        "PATIENT ATLAS REGISTRATION"
    )

    print(
        "=" * 60
    )

    print(
        "Patient:",
        args.patient_id,
    )

    print(
        "Timepoint:",
        args.timepoint,
    )

    print(
        "Selected stage:",
        result.selected_stage,
    )

    print(
        "Automatic QC:",
        quality.status,
    )

    print(
        "Brain Dice:",
        f"{quality.brain_dice:.4f}",
    )

    print(
        "Labels inside brain:",
        (
            f"{quality.labeled_inside_brain_fraction:.4f}"
        ),
    )

    print(
        "Metric value:",
        f"{result.metric_value:.6f}",
    )

    print(
        "Candidate labels:",
        result.candidate_labels_path,
    )

    print(
        "Registered template:",
        result.registered_template_path,
    )

    print(
        "Registered brain mask:",
        result.registered_brain_mask_path,
    )

    print(
        "Linear transform:",
        result.linear_transform_path,
    )

    print(
        "Deformable transform:",
        result.deformable_transform_path,
    )

    print(
        "Provenance:",
        result.provenance_path,
    )

    print()
    print(
        "Manual review is required."
    )

    print(
        "No canonical labels.nii.gz "
        "has been created."
    )


if __name__ == "__main__":
    main()