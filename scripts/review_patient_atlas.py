from __future__ import annotations

import argparse
import os
from pathlib import Path

from gbm_twin.anatomy.registration_review import (
    ReviewDecision,
    review_registration,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Manually accept or reject "
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
        "--decision",
        choices=(
            "accepted",
            "rejected",
        ),
        required=True,
    )

    parser.add_argument(
        "--reviewer",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--notes",
        type=str,
        default=None,
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

    if args.atlas_root is None:
        parser.error(
            "--atlas-root is required, "
            "or set GBM_TWIN_ATLAS_ROOT"
        )

    atlas_root = (
        args.atlas_root.resolve()
    )

    registration_dir = (
        atlas_root
        / "patients"
        / str(
            args.patient_id
        )
        / args.timepoint
    )

    decision: ReviewDecision = (
        args.decision
    )

    result = review_registration(
        registration_dir=(
            registration_dir
        ),
        patient_id=(
            args.patient_id
        ),
        timepoint_name=(
            args.timepoint
        ),
        decision=(
            decision
        ),
        reviewer=(
            args.reviewer
        ),
        notes=(
            args.notes
        ),
    )

    print()
    print(
        "REGISTRATION REVIEW"
    )

    print(
        "=" * 60
    )

    print(
        "Patient:",
        result.patient_id,
    )

    print(
        "Timepoint:",
        result.timepoint_name,
    )

    print(
        "Decision:",
        result.decision,
    )

    print(
        "Automatic QC:",
        result.automatic_qc_status,
    )

    print(
        "Reviewer:",
        result.reviewer,
    )

    if result.notes is not None:
        print(
            "Notes:",
            result.notes,
        )

    if result.decision == "accepted":
        print(
            "Canonical labels.nii.gz "
            "created."
        )

    else:
        print(
            "Canonical labels.nii.gz "
            "is absent."
        )


if __name__ == "__main__":
    main()