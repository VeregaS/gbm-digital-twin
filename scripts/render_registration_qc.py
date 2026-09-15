from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import cast

import nibabel as nib
import numpy as np
from nibabel.nifti1 import Nifti1Image

from gbm_twin.anatomy.qc import (
    render_registration_qc_png,
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

    normalized = value.strip()

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


def _load_array(
    path: Path,
) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required QC volume "
            f"not found: {path}"
        )

    image = cast(
        Nifti1Image,
        nib.load(
            str(path)
        ),
    )

    return np.asarray(
        image.dataobj
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render visual QC for "
            "an anatomical atlas "
            "registration candidate."
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

    registration_dir = (
        atlas_root
        / "patients"
        / str(
            args.patient_id
        )
        / args.timepoint
    )

    registered_brain = (
        _load_array(
            registration_dir
            / (
                "atlas_brain_mask_"
                "registered.nii.gz"
            )
        )
    )

    candidate_labels = (
        _load_array(
            registration_dir
            / "labels_candidate.nii.gz"
        )
    )

    output_path = (
        registration_dir
        / "registration_qc.png"
    )

    result = (
        render_registration_qc_png(
            patient_t1=(
                prepared.t1gd.data
            ),
            patient_brain_mask=(
                prepared
                .brain_mask
                .data
            ),
            registered_atlas_brain_mask=(
                registered_brain
            ),
            registered_labels=(
                candidate_labels
            ),
            output_path=(
                output_path
            ),
            patient_id=(
                args.patient_id
            ),
            timepoint_name=(
                args.timepoint
            ),
        )
    )

    print()
    print(
        "REGISTRATION VISUAL QC"
    )

    print(
        "=" * 60
    )

    print(
        "Brain Dice:",
        f"{result.brain_dice:.4f}",
    )

    print(
        "Labels inside brain:",
        (
            f"{result.labeled_inside_brain_fraction:.4f}"
        ),
    )

    print(
        "QC image:",
        result.output_path,
    )

    print()
    print(
        "This is a candidate only."
    )

    print(
        "Explicit manual review "
        "is required before anatomy "
        "analysis can use it."
    )


if __name__ == "__main__":
    main()