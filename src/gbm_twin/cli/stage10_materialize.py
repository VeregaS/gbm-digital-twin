from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from gbm_twin.cli import stage10_validate as defaults
from gbm_twin.workflows.stage10_materialization import materialize_stage10_reserve


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Materialize only the verified sealed Stage 10 reserve cohort."
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    for flag, default in (
        ("experiment-config", defaults.DEFAULT_EXPERIMENT_CONFIG),
        ("stage8-protocol", defaults.DEFAULT_STAGE8_PROTOCOL),
        ("data-audit-root", defaults.DEFAULT_AUDIT_ROOT),
        ("stage8-selection-root", defaults.DEFAULT_STAGE8_SELECTION_ROOT),
        ("stage10-selection-root", defaults.DEFAULT_STAGE10_SELECTION_ROOT),
        ("frozen-model-config", defaults.DEFAULT_FROZEN_MODEL_CONFIG),
        ("validation-config", defaults.DEFAULT_VALIDATION_CONFIG),
        ("validation-plan-root", defaults.DEFAULT_PLAN_ROOT),
    ):
        parser.add_argument(f"--{flag}", type=Path, default=default)
    parser.add_argument("--source-data-root", type=Path)
    parser.add_argument("--mode", choices=("auto", "hardlink", "copy"), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--download-missing",
        action="store_true",
        help="Fetch only sealed required files from official TCIA version 4.",
    )
    parser.add_argument("--ascp-path", type=Path, help="Installed Aspera ascp executable.")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()

    def resolve(path: Path) -> Path:
        return path if path.is_absolute() else repo / path

    try:
        result = materialize_stage10_reserve(
            repo_root=repo,
            experiment_config_path=resolve(args.experiment_config),
            stage8_protocol_path=resolve(args.stage8_protocol),
            data_audit_root=resolve(args.data_audit_root),
            stage8_selection_root=resolve(args.stage8_selection_root),
            stage10_selection_root=resolve(args.stage10_selection_root),
            frozen_model_config_path=resolve(args.frozen_model_config),
            validation_config_path=resolve(args.validation_config),
            validation_plan_root=resolve(args.validation_plan_root),
            source_data_root=(
                None if args.source_data_root is None else resolve(args.source_data_root)
            ),
            mode=args.mode,
            dry_run=args.dry_run,
            download_missing=args.download_missing,
            ascp_path=args.ascp_path,
            progress=lambda message: print(message, flush=True),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Sealed patients: {','.join(map(str, result.patient_ids))}")
    print(f"Source: {result.source_root}\nDestination: {result.destination_root}")
    print(
        f"Created: {result.created_count}; reused: {result.reused_count}; dry run: {result.dry_run}"
    )
    return 0
