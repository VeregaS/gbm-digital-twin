from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage8_validation_plan import (
    create_stage8_validation_plan,
)

DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit-v1")
DEFAULT_SELECTION_ROOT = Path("results/cohort/stage8-model-selection-v1")
DEFAULT_OUTPUT_ROOT = Path(
    "results/cohort/stage8-internal-validation-plan-v1"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    data_audit_root: Path
    selection_root: Path
    output_dir: Path
    patient_count: int
    seed: int


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Seal a compact metadata-stratified Stage 8 internal-validation "
            "cohort before any validation t2 image is opened."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
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
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--patient-count",
        type=int,
        default=16,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260919,
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
        result = create_stage8_validation_plan(
            data_audit_root=_resolve(repo_root, args.data_audit_root),
            selection_root=_resolve(repo_root, args.selection_root),
            output_dir=_resolve(repo_root, args.output_dir),
            patient_count=args.patient_count,
            seed=args.seed,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Stage 8 validation plan created: {result.directory}")
    print(f"Patients: {len(result.patient_ids)}")
    print("Patient IDs: " + ", ".join(str(x) for x in result.patient_ids))
    print(
        f"Reserved non-holdout patients: "
        f"{64 - len(result.patient_ids)} or audit-dependent remainder"
    )
    print("Selection used metadata only; validation t2 was not loaded.")
    return 0
