from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.stage8_selection import select_stage8_model_family

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_PROTOCOL_CONFIG = Path("configs/research/stage8_protocol.yaml")
DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit")
DEFAULT_CACHE_ROOT = Path("results/cache/stage8-selection")
DEFAULT_OUTPUT_DIR = Path("results/cohort/stage8-model-selection")


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    protocol_config: Path
    data_audit_root: Path
    cache_root: Path
    output_dir: Path
    workers: int
    allow_dirty: bool


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select Stage 8 mechanisms through sequential nested ablations "
            "using development-exposed patients only."
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
        help="Allow non-reproducible development runs from a dirty Git tree.",
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
        result = select_stage8_model_family(
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
            cache_root=_resolve(repo_root, args.cache_root),
            output_dir=_resolve(repo_root, args.output_dir),
            workers=args.workers,
            allow_dirty=args.allow_dirty,
        )

        selected = result.manifest.get("selected_candidate")
        phases = result.manifest.get("phases")
        if not isinstance(selected, dict) or not isinstance(phases, list):
            raise ValueError("Generated Stage 8 selection artifact is incomplete")
        if not phases or not isinstance(phases[-1], dict):
            raise ValueError("Stage 8 selection has no final phase")
        loo = phases[-1].get("loo")
        if not isinstance(loo, dict):
            raise ValueError("Stage 8 final phase has no LOO summary")

    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Stage 8 model selection created: {result.directory}")
    print(
        "Leakage contract: t2 was loaded only for development-exposed "
        "patients; internal-validation and untouched-holdout t2 were not loaded."
    )
    print("Nested ablation phases:")
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        print(
            f"  {phase.get('phase')}: "
            f"{phase.get('selected_candidate_id')}"
        )
    print(f"Selected candidate: {selected}")
    print(
        "Final-phase LOO: mean Dice="
        f"{float(loo['mean_dice']):.4f}, "
        "median Dice="
        f"{float(loo['median_dice']):.4f}, "
        "mean volume error="
        f"{float(loo['mean_relative_volume_error']):.4f}"
    )
    print(
        "Artifacts: stage8_model_selection.json, "
        "stage8_model_selection.sha256, stage8_model_selection.csv"
    )
    return 0
