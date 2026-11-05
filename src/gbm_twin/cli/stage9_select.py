from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage9_selection import (
    select_stage9_delayed_response,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_STAGE8_PROTOCOL = Path("configs/research/stage8_protocol.yaml")
DEFAULT_STAGE9_PROTOCOL = Path(
    "configs/research/stage9_delayed_response.yaml"
)
DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit-v1")
DEFAULT_STAGE8_SELECTION_ROOT = Path(
    "results/cohort/stage8-model-selection-v1"
)
DEFAULT_STAGE8_VALIDATION_ROOT = Path(
    "results/cohort/stage8-internal-validation-v1"
)
DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/stage9-delayed-selection-v1"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    stage8_protocol: Path
    stage9_protocol: Path
    data_audit_root: Path
    stage8_selection_root: Path
    stage8_validation_root: Path
    output_dir: Path
    allow_dirty: bool


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select a Stage 9 delayed radiation-response model while "
            "freezing patient-specific Stage 8 D/rho."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--stage8-protocol",
        type=Path,
        default=DEFAULT_STAGE8_PROTOCOL,
    )
    parser.add_argument(
        "--stage9-protocol",
        type=Path,
        default=DEFAULT_STAGE9_PROTOCOL,
    )
    parser.add_argument(
        "--data-audit-root",
        type=Path,
        default=DEFAULT_AUDIT_ROOT,
    )
    parser.add_argument(
        "--stage8-selection-root",
        type=Path,
        default=DEFAULT_STAGE8_SELECTION_ROOT,
    )
    parser.add_argument(
        "--stage8-validation-root",
        type=Path,
        default=DEFAULT_STAGE8_VALIDATION_ROOT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a non-reproducible run from a dirty Git tree.",
    )
    return parser


def parse_arguments(argv: Sequence[str] | None = None) -> CliArguments:
    return cast(
        CliArguments,
        build_parser().parse_args(
            None if argv is None else list(argv),
            namespace=CliArguments(),
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    repo_root = args.repo_root.resolve()

    try:
        result = select_stage9_delayed_response(
            repo_root=repo_root,
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            stage8_protocol_path=_resolve(
                repo_root,
                args.stage8_protocol,
            ),
            stage9_protocol_path=_resolve(
                repo_root,
                args.stage9_protocol,
            ),
            data_audit_root=_resolve(
                repo_root,
                args.data_audit_root,
            ),
            stage8_selection_root=_resolve(
                repo_root,
                args.stage8_selection_root,
            ),
            stage8_validation_root=_resolve(
                repo_root,
                args.stage8_validation_root,
            ),
            output_dir=_resolve(repo_root, args.output_dir),
            allow_dirty=args.allow_dirty,
            progress=lambda message: print(message, flush=True),
        )
        selected = result.manifest.get("selected_candidate")
        summary = result.manifest.get("selected_summary")
        leakage = result.manifest.get("leakage_control")
        control = result.manifest.get("stage8_control")
        trajectory = result.manifest.get("trajectory_analysis")
        if (
            not isinstance(selected, dict)
            or not isinstance(summary, dict)
            or not isinstance(leakage, dict)
            or not isinstance(control, dict)
            or not isinstance(trajectory, dict)
        ):
            raise ValueError("Generated Stage 9 selection is incomplete")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print()
    print(f"Stage 9 selection created: {result.directory}")
    print(f"Selected candidate: {selected['candidate_id']}")
    print(
        "Mean Dice: "
        f"{float(summary['mean_dice']):.4f}"
    )
    print(
        "Mean delta vs persistence: "
        f"{float(summary['mean_delta_vs_persistence']):+.4f}"
    )
    print(
        "Mean Dice gain vs exact Stage 8 control: "
        f"{float(summary['mean_dice']) - float(control['mean_dice']):+.4f}"
    )
    print(
        "Catastrophic failures: "
        f"{int(summary['catastrophic_failure_count'])}"
    )
    selected_trajectory = trajectory.get("selected_candidate")
    if isinstance(selected_trajectory, dict):
        regression = selected_trajectory.get("regression")
        if isinstance(regression, dict) and regression.get("patient_count"):
            print(
                "Regression subgroup mean delta vs persistence: "
                f"{float(regression['mean_delta_vs_persistence']):+.4f}"
            )

    print(
        "Development patients: "
        f"{len(cast(list[object], leakage['development_patient_ids']))}"
    )
    print(
        "Reserve patients kept unopened: "
        f"{len(cast(list[object], leakage['reserve_patient_ids']))}"
    )
    print("Untouched holdout t2 was not loaded.")
    return 0
