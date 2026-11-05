from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage9_validation_plan import (
    create_stage9_validation_plan,
)

DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit-v1")
DEFAULT_STAGE9_SELECTION_ROOT = Path(
    "results/cohort/stage9-delayed-selection-v1"
)
DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/stage9-reserve-validation-plan-v1"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    data_audit_root: Path
    stage9_selection_root: Path
    output_dir: Path
    patient_count: int
    seed: int


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seal a compact Stage 9 reserve-validation cohort without "
            "opening reserve or untouched-holdout t2."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--data-audit-root",
        type=Path,
        default=DEFAULT_AUDIT_ROOT,
    )
    parser.add_argument(
        "--stage9-selection-root",
        type=Path,
        default=DEFAULT_STAGE9_SELECTION_ROOT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument("--patient-count", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20260920)
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
        result = create_stage9_validation_plan(
            data_audit_root=_resolve(
                repo_root,
                args.data_audit_root,
            ),
            stage9_selection_root=_resolve(
                repo_root,
                args.stage9_selection_root,
            ),
            output_dir=_resolve(repo_root, args.output_dir),
            patient_count=args.patient_count,
            seed=args.seed,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Stage 9 validation plan created: {result.directory}")
    print(f"Patients: {len(result.patient_ids)}")
    print("Patient IDs: " + ", ".join(str(x) for x in result.patient_ids))
    print(
        f"Remaining reserve patients: {len(result.reserve_patient_ids)}"
    )
    print("Untouched holdout t2 was not loaded.")
    print(
        "Download manifests: stage9_validation_patient_ids.txt, "
        "stage9_validation_required_paths.txt"
    )
    return 0
