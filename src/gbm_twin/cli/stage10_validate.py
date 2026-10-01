from __future__ import annotations

import argparse
import sys
from collections.abc import (
    Sequence,
)
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage10_validation import (
    validate_stage10_model,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)

DEFAULT_STAGE8_PROTOCOL = Path(
    "configs/research/stage8_protocol.yaml"
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

DEFAULT_PLAN_ROOT = Path(
    "results/cohort/stage10-reserve-validation-plan-v1"
)

DEFAULT_CACHE_ROOT = Path(
    "results/cache/stage10-reserve-validation-v1"
)

DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/stage10-internal-validation-v1"
)


class CliArguments(
    argparse.Namespace
):
    repo_root: Path
    experiment_config: Path
    stage8_protocol: Path
    data_audit_root: Path
    stage8_selection_root: Path
    stage10_selection_root: Path
    frozen_model_config: Path
    validation_config: Path
    validation_plan_root: Path
    cache_root: Path
    output_dir: Path
    workers: int
    allow_dirty: bool


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
            "Evaluate the frozen Stage 10 model on the sealed reserve cohort. "
            "D/rho are frozen from t0/t1 before each patient t2 is opened."
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
        "--experiment-config",
        type=Path,
        default=(
            DEFAULT_EXPERIMENT_CONFIG
        ),
    )

    parser.add_argument(
        "--stage8-protocol",
        type=Path,
        default=(
            DEFAULT_STAGE8_PROTOCOL
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
        "--validation-plan-root",
        type=Path,
        default=(
            DEFAULT_PLAN_ROOT
        ),
    )

    parser.add_argument(
        "--cache-root",
        type=Path,
        default=(
            DEFAULT_CACHE_ROOT
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            DEFAULT_OUTPUT_DIR
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--allow-dirty",
        action="store_true",
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
            validate_stage10_model(
                repo_root=(
                    repo_root
                ),
                experiment_config_path=(
                    _resolve(
                        repo_root,
                        args.experiment_config,
                    )
                ),
                stage8_protocol_path=(
                    _resolve(
                        repo_root,
                        args.stage8_protocol,
                    )
                ),
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
                validation_plan_root=(
                    _resolve(
                        repo_root,
                        args.validation_plan_root,
                    )
                ),
                cache_root=(
                    _resolve(
                        repo_root,
                        args.cache_root,
                    )
                ),
                output_dir=(
                    _resolve(
                        repo_root,
                        args.output_dir,
                    )
                ),
                workers=(
                    args.workers
                ),
                allow_dirty=(
                    args.allow_dirty
                ),
                progress=(
                    lambda message: print(
                        message,
                        flush=True,
                    )
                ),
            )
        )

        summary = (
            result.manifest.get(
                "summary"
            )
        )

        if not isinstance(
            summary,
            dict,
        ):
            raise ValueError(
                "Generated Stage 10 validation has no summary"
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

    print()

    print(
        "Stage 10 validation created:",
        result.directory,
    )

    print(
        "Decision:",
        result.manifest.get(
            "decision"
        ),
    )

    print(
        "Patients:",
        int(
            summary[
                "patient_count"
            ]
        ),
    )

    print(
        "Twin mean Dice: "
        f"{float(summary['mean_twin_dice']):.4f}"
    )

    print(
        "Persistence mean Dice: "
        f"{float(summary['mean_persistence_dice']):.4f}"
    )

    print(
        "Mean Dice delta vs persistence: "
        f"{float(summary['mean_delta_vs_persistence']):+.4f}"
    )

    print(
        "Median Dice delta vs persistence: "
        f"{float(summary['median_delta_vs_persistence']):+.4f}"
    )

    print(
        "Catastrophic failures: "
        f"{int(summary['catastrophic_failure_count'])}"
    )

    print(
        "Untouched holdout t2 was not loaded."
    )

    return 0
