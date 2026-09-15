from __future__ import annotations

import argparse
import os
from pathlib import Path

from gbm_twin.anatomy.source_qc import (
    render_anatomy_source_qc,
)
from gbm_twin.workflows.patients import (
    prepare_patient_timepoint,
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
            "Render independent source "
            "QC for patient anatomy "
            "and anatomical atlas."
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

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--tile-size",
        type=int,
        default=320,
    )

    return parser


def main() -> None:
    parser = build_parser()

    args = parser.parse_args()

    if args.patient_id <= 0:
        parser.error(
            "--patient-id must "
            "be positive"
        )

    if args.tile_size < 128:
        parser.error(
            "--tile-size must "
            "be at least 128"
        )

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

    prepared = (
        prepare_patient_timepoint(
            metadata_root=(
                metadata_root
            ),
            patients_root=(
                patients_root
            ),
            patient_id=(
                args.patient_id
            ),
            timepoint_name=(
                args.timepoint
            ),
        )
    )

    if args.output_dir is None:
        output_dir = (
            atlas_root
            / "patients"
            / str(
                args.patient_id
            )
            / args.timepoint
            / "source_qc"
        )

    else:
        output_dir = (
            args.output_dir.resolve()
        )

    result = (
        render_anatomy_source_qc(
            patient_t1=(
                prepared.t1gd.data
            ),
            patient_brain_mask=(
                prepared
                .brain_mask
                .data
            ),
            atlas_template_path=(
                atlas_root
                / "template_t1.nii.gz"
            ),
            atlas_brain_mask_path=(
                atlas_root
                / (
                    "template_"
                    "brain_mask.nii.gz"
                )
            ),
            atlas_labels_path=(
                atlas_root
                / (
                    "template_"
                    "labels.nii.gz"
                )
            ),
            output_dir=(
                output_dir
            ),
            patient_id=(
                args.patient_id
            ),
            timepoint_name=(
                args.timepoint
            ),
            tile_size=(
                args.tile_size
            ),
        )
    )

    print()
    print(
        "ANATOMY SOURCE QC"
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
        "Patient brain voxels:",
        (
            result.metrics
            .patient_brain_voxels
        ),
    )

    print(
        "Atlas brain voxels:",
        (
            result.metrics
            .atlas_brain_voxels
        ),
    )

    print(
        "Atlas label voxels:",
        (
            result.metrics
            .atlas_label_voxels
        ),
    )

    print(
        "Atlas labels inside "
        "atlas brain:",
        (
            f"{result.metrics.atlas_labels_inside_brain_fraction:.4f}"
        ),
    )

    print(
        "Patient QC:",
        (
            result
            .patient_image_path
        ),
    )

    print(
        "Atlas QC:",
        (
            result
            .atlas_image_path
        ),
    )

    print(
        "Report:",
        result.report_path,
    )


if __name__ == "__main__":
    main()