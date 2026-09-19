from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage8_materialization import (
    MaterializationMode,
    materialize_stage8_internal_validation,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit-v1")
DEFAULT_SELECTION_ROOT = Path("results/cohort/stage8-model-selection-v1")


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    data_audit_root: Path
    selection_root: Path
    source_data_root: Path | None
    mode: MaterializationMode
    dry_run: bool


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize the sealed Stage 8 internal-validation cohort from "
            "the official CFB-GBM NIfTI data tree without changing the split."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--data-audit-root",
        type=Path,
        default=DEFAULT_AUDIT_ROOT,
    )
    parser.add_argument(
        "--selection-root",
        type=Path,
        default=DEFAULT_SELECTION_ROOT,
    )
    parser.add_argument(
        "--source-data-root",
        type=Path,
        help=(
            "Official CFB-GBM data/ directory. Defaults to "
            "GBM_TWIN_CFB_SOURCE_DATA_ROOT, then GBM_TWIN_CFB_ROOT/data, "
            "then the sibling data/ directory next to patients/."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "hardlink", "copy"),
        default="auto",
        help=(
            "auto tries hardlinks first and falls back to copy. "
            "Hardlinks avoid duplicating large NIfTI files."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the source and print the plan without writing files.",
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
        result = materialize_stage8_internal_validation(
            repo_root=repo_root,
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            data_audit_root=_resolve(
                repo_root,
                args.data_audit_root,
            ),
            selection_root=_resolve(
                repo_root,
                args.selection_root,
            ),
            source_data_root=(
                None
                if args.source_data_root is None
                else _resolve(repo_root, args.source_data_root)
            ),
            mode=args.mode,
            dry_run=args.dry_run,
            progress=lambda message: print(message, flush=True),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print()
    print("Stage 8 internal-validation materialization complete.")
    print(f"Source: {result.source_root}")
    print(f"Destination: {result.destination_root}")
    print(f"Patients: {len(result.patient_ids)}")
    print(f"Required inputs: {result.required_count}")
    print(f"Created: {result.created_count}")
    print(f"Reused: {result.reused_count}")
    print(f"Hardlinks: {result.hardlink_count}")
    print(f"Copies: {result.copy_count}")
    print(f"Dry run: {result.dry_run}")
    return 0
