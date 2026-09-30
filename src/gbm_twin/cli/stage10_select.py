from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage10_selection import (
    select_stage10_decoupled_damage,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)

DEFAULT_STAGE8_PROTOCOL = Path(
    "configs/research/stage8_protocol.yaml"
)

DEFAULT_STAGE10_PROTOCOL = Path(
    "configs/research/stage10_decoupled_damage.yaml"
)

DEFAULT_AUDIT_ROOT = Path(
    "results/cohort/stage8-data-audit-v1"
)

DEFAULT_STAGE8_SELECTION_ROOT = Path(
    "results/cohort/stage8-model-selection-v1"
)

DEFAULT_STAGE8_VALIDATION_ROOT = Path(
    "results/cohort/stage8-internal-validation-v1"
)

DEFAULT_STAGE9_SELECTION_ROOT = Path(
    "results/cohort/stage9-delayed-selection-v2"
)

DEFAULT_REFERENCE_FIDELITY_ROOT = Path(
    "results/cohort/reference-fidelity-v2"
)

DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/stage10-decoupled-selection-v1"
)


class CliArguments(
    argparse.Namespace
):
    repo_root: Path
    experiment_config: Path
    stage8_protocol: Path
    stage10_protocol: Path
    data_audit_root: Path
    stage8_selection_root: Path
    stage8_validation_root: Path
    stage9_selection_root: Path
    reference_fidelity_root: Path
    output_dir: Path
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
            "Run the Stage 10 development-only decoupled-damage "
            "diagnostic while keeping Stage 8 D/rho frozen."
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
        "--stage10-protocol",
        type=Path,
        default=(
            DEFAULT_STAGE10_PROTOCOL
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
        "--stage8-validation-root",
        type=Path,
        default=(
            DEFAULT_STAGE8_VALIDATION_ROOT
        ),
    )

    parser.add_argument(
        "--stage9-selection-root",
        type=Path,
        default=(
            DEFAULT_STAGE9_SELECTION_ROOT
        ),
    )

    parser.add_argument(
        "--reference-fidelity-root",
        type=Path,
        default=(
            DEFAULT_REFERENCE_FIDELITY_ROOT
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
        "--allow-dirty",
        action="store_true",
        help=(
            "Allow a non-reproducible run from a dirty Git tree."
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
            select_stage10_decoupled_damage(
                repo_root=repo_root,
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
                stage10_protocol_path=(
                    _resolve(
                        repo_root,
                        args.stage10_protocol,
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
                stage8_validation_root=(
                    _resolve(
                        repo_root,
                        args.stage8_validation_root,
                    )
                ),
                stage9_selection_root=(
                    _resolve(
                        repo_root,
                        args.stage9_selection_root,
                    )
                ),
                reference_fidelity_root=(
                    _resolve(
                        repo_root,
                        args.reference_fidelity_root,
                    )
                ),
                output_dir=(
                    _resolve(
                        repo_root,
                        args.output_dir,
                    )
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

        selected = (
            result.manifest.get(
                "selected_candidate"
            )
        )

        summary = (
            result.manifest.get(
                "selected_summary"
            )
        )

        control = (
            result.manifest.get(
                "control_summary"
            )
        )

        leakage = (
            result.manifest.get(
                "leakage_control"
            )
        )

        decision = (
            result.manifest.get(
                "decision"
            )
        )

        if not all(
            isinstance(
                value,
                dict,
            )
            for value in (
                selected,
                summary,
                control,
                leakage,
            )
        ):
            raise ValueError(
                "Generated Stage 10 selection is incomplete"
            )

        selected = cast(
            dict[
                str,
                object,
            ],
            selected,
        )

        summary = cast(
            dict[
                str,
                object,
            ],
            summary,
        )

        control = cast(
            dict[
                str,
                object,
            ],
            control,
        )

        leakage = cast(
            dict[
                str,
                object,
            ],
            leakage,
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
        "Stage 10 selection created:",
        result.directory,
    )

    print(
        "Decision:",
        decision,
    )

    print(
        "Selected candidate:",
        selected[
            "candidate_id"
        ],
    )

    print(
        "Mean Dice: "
        f"{float(summary['mean_dice']):.4f}"
    )

    print(
        "Mean delta vs persistence: "
        f"{float(summary['mean_delta_vs_persistence']):+.4f}"
    )

    print(
        "Catastrophic failures: "
        f"{int(summary['catastrophic_failure_count'])}"
    )

    print(
        "Control catastrophic failures: "
        f"{int(control['catastrophic_failure_count'])}"
    )

    regression = (
        summary.get(
            "regression_mean_delta_vs_persistence"
        )
    )

    if regression is not None:
        print(
            "Regression subgroup mean delta vs persistence: "
            f"{float(regression):+.4f}"
        )

    development_ids = cast(
        list[
            object
        ],
        leakage[
            "development_patient_ids"
        ],
    )

    reserve_ids = cast(
        list[
            object
        ],
        leakage[
            "reserve_patient_ids"
        ],
    )

    print(
        "Development patients:",
        len(
            development_ids
        ),
    )

    print(
        "Reserve patients kept unopened:",
        len(
            reserve_ids
        ),
    )

    print(
        "Untouched holdout t2 was not loaded."
    )

    return 0
