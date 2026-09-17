from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage8_validation import validate_selected_stage8_model

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_PROTOCOL_CONFIG = Path("configs/research/stage8_protocol.yaml")
DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit")
DEFAULT_SELECTION_ROOT = Path("results/cohort/stage8-model-selection")
DEFAULT_CACHE_ROOT = Path("results/cache/stage8-internal-validation")
DEFAULT_OUTPUT_DIR = Path("results/cohort/stage8-internal-validation")


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    protocol_config: Path
    data_audit_root: Path
    selection_root: Path
    cache_root: Path
    output_dir: Path
    workers: int
    allow_dirty: bool


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the sealed Stage 8 model once on internal-validation "
            "patients without revealing untouched-holdout t2."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--protocol-config",
        type=Path,
        default=DEFAULT_PROTOCOL_CONFIG,
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
        "--cache-root",
        type=Path,
        default=DEFAULT_CACHE_ROOT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a non-reproducible validation run from a dirty Git tree.",
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
        result = validate_selected_stage8_model(
            repo_root=repo_root,
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            protocol_config_path=_resolve(
                repo_root,
                args.protocol_config,
            ),
            data_audit_root=_resolve(
                repo_root,
                args.data_audit_root,
            ),
            selection_root=_resolve(
                repo_root,
                args.selection_root,
            ),
            cache_root=_resolve(repo_root, args.cache_root),
            output_dir=_resolve(repo_root, args.output_dir),
            workers=args.workers,
            allow_dirty=args.allow_dirty,
        )
        summary = result.manifest.get("summary")
        if not isinstance(summary, dict):
            raise ValueError("Generated Stage 8 validation has no summary")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Stage 8 internal validation created: {result.directory}")
    print(
        "Leakage contract: internal-validation t2 was revealed only after "
        "model selection; untouched-holdout t2 was not loaded."
    )
    print(f"Patients: {int(summary['patient_count'])}")
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
        "Artifacts: stage8_internal_validation.json, "
        "stage8_internal_validation.sha256, "
        "stage8_internal_validation.csv"
    )
    return 0
