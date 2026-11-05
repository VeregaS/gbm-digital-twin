from __future__ import annotations

import argparse
import sys
from collections.abc import (
    Sequence,
)
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage10_validation_plan import (
    create_stage10_validation_plan,
)

DEFAULT_AUDIT_ROOT = Path(
    "results/cohort/stage8-data-audit-v1"
)

DEFAULT_STAGE8_SELECTION_ROOT = Path(
    "results/cohort/stage8-model-selection-v1"
)

DEFAULT_STAGE10_SELECTION_ROOT = Path(
    "results/cohort/stage10-decoupled-selection-v1"
)

DEFAULT_FROZEN_MODEL_CONFIG = Path(
    "configs/research/stage10_frozen_model.yaml"
)

DEFAULT_VALIDATION_CONFIG = Path(
    "configs/research/stage10_reserve_validation.yaml"
)

DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/stage10-reserve-validation-plan-v1"
)


class CliArguments(
    argparse.Namespace
):
    repo_root: Path
    data_audit_root: Path
    stage8_selection_root: Path
    stage10_selection_root: Path
    frozen_model_config: Path
    validation_config: Path
    output_dir: Path


def _resolve(
    repo_root: Path,
    path: Path,
) -> Path:
    return (
        path
        if path.is_absolute()
        else repo_root
        / path
    )


def build_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seal the Stage 10 reserve-validation cohort without "
            "opening reserve or untouched-holdout t2."
        )
    )

    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(
            "."
        ),
    )

    parser.add_argument(
        "--data-audit-root",
        type=Path,
        default=(
            DEFAULT_AUDIT_ROOT
        ),
    )

    parser.add_argument(
        "--stage8-selection-root",
        type=Path,
        default=(
            DEFAULT_STAGE8_SELECTION_ROOT
        ),
    )

    parser.add_argument(
        "--stage10-selection-root",
        type=Path,
        default=(
            DEFAULT_STAGE10_SELECTION_ROOT
        ),
    )

    parser.add_argument(
        "--frozen-model-config",
        type=Path,
        default=(
            DEFAULT_FROZEN_MODEL_CONFIG
        ),
    )

    parser.add_argument(
        "--validation-config",
        type=Path,
        default=(
            DEFAULT_VALIDATION_CONFIG
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            DEFAULT_OUTPUT_DIR
        ),
    )

    return parser


def parse_arguments(
    argv: Sequence[
        str
    ]
    | None = None,
) -> CliArguments:
    return cast(
        CliArguments,
        build_parser().parse_args(
            (
                None
                if argv is None
                else list(
                    argv
                )
            ),
            namespace=(
                CliArguments()
            ),
        ),
    )


def main(
    argv: Sequence[
        str
    ]
    | None = None,
) -> int:
    args = parse_arguments(
        argv
    )

    repo_root = (
        args.repo_root.resolve()
    )

    try:
        result = (
            create_stage10_validation_plan(
                data_audit_root=(
                    _resolve(
                        repo_root,
                        args.data_audit_root,
                    )
                ),
                stage8_selection_root=(
                    _resolve(
                        repo_root,
                        args.stage8_selection_root,
                    )
                ),
                stage10_selection_root=(
                    _resolve(
                        repo_root,
                        args.stage10_selection_root,
                    )
                ),
                frozen_model_config_path=(
                    _resolve(
                        repo_root,
                        args.frozen_model_config,
                    )
                ),
                validation_config_path=(
                    _resolve(
                        repo_root,
                        args.validation_config,
                    )
                ),
                output_dir=(
                    _resolve(
                        repo_root,
                        args.output_dir,
                    )
                ),
            )
        )

    except (
        OSError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(
            f"Error: {exc}",
            file=sys.stderr,
        )

        return 1

    print(
        "Stage 10 validation plan created:",
        result.directory,
    )

    print(
        "Patients:",
        len(
            result.patient_ids
        ),
    )

    print(
        "Patient IDs:",
        ", ".join(
            str(
                value
            )
            for value in (
                result.patient_ids
            )
        ),
    )

    print(
        "Remaining sealed reserve patients:",
        len(
            result
            .remaining_reserve_patient_ids
        ),
    )

    print(
        "Untouched holdout t2 was not loaded."
    )

    return 0
