from __future__ import annotations

import argparse
from pathlib import Path

from gbm_twin.anatomy.bootstrap import (
    bootstrap_harvard_oxford_atlas,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download and prepare "
            "the anatomical atlas "
            "used by GBM Digital Twin."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help=(
            "Atlas root directory."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "Remove and recreate an "
            "existing non-empty "
            "atlas directory."
        ),
    )

    return parser


def main() -> None:
    parser = build_parser()

    args = parser.parse_args()

    result = (
        bootstrap_harvard_oxford_atlas(
            args.output,
            overwrite=(
                args.overwrite
            ),
        )
    )

    print()
    print(
        "ANATOMICAL ATLAS BOOTSTRAP"
    )
    print(
        "=" * 60
    )

    print(
        "Atlas root:",
        result.atlas_root,
    )

    print(
        "Template T1:",
        result.template_path,
    )

    print(
        "Template brain mask:",
        result.brain_mask_path,
    )

    print(
        "Template labels:",
        result.labelmap_path,
    )

    print(
        "Manifest:",
        result.manifest_path,
    )

    print(
        "Functional-risk regions:",
        result.region_count,
    )


if __name__ == "__main__":
    main()