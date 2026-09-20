from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.reference_benchmark import run_reference_benchmark

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_STAGE8_PROTOCOL = Path("configs/research/stage8_protocol.yaml")
DEFAULT_STAGE8_SELECTION_ROOT = Path(
    "results/cohort/stage8-model-selection-v1"
)
DEFAULT_STAGE9_SELECTION_ROOT = Path(
    "results/cohort/stage9-delayed-selection-v2"
)
DEFAULT_TUMORTWIN_PYTHON = Path(
    ".reference/tumortwin-venv/Scripts/python.exe"
)
DEFAULT_WORKER_SCRIPT = Path("scripts/reference/tumortwin_worker.py")
DEFAULT_CACHE_ROOT = Path("results/cache/reference-tumortwin-v1")
DEFAULT_OUTPUT_DIR = Path("results/cohort/reference-benchmark-v1")


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    stage8_protocol: Path
    stage8_selection_root: Path
    stage9_selection_root: Path
    tumortwin_python: Path
    worker_script: Path
    cache_root: Path
    output_dir: Path
    frozen_only: bool
    calibrated_only: bool
    optimizer_iterations: int
    allow_dirty: bool


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark the pinned upstream TumorTwin implementation against "
            "the same exposed CFB development cohort and persistence baseline."
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
        "--stage8-selection-root",
        type=Path,
        default=DEFAULT_STAGE8_SELECTION_ROOT,
    )
    parser.add_argument(
        "--stage9-selection-root",
        type=Path,
        default=DEFAULT_STAGE9_SELECTION_ROOT,
    )
    parser.add_argument(
        "--tumortwin-python",
        type=Path,
        default=DEFAULT_TUMORTWIN_PYTHON,
    )
    parser.add_argument(
        "--worker-script",
        type=Path,
        default=DEFAULT_WORKER_SCRIPT,
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--frozen-only", action="store_true")
    mode.add_argument("--calibrated-only", action="store_true")
    parser.add_argument("--optimizer-iterations", type=int, default=8)
    parser.add_argument("--allow-dirty", action="store_true")
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
        artifact = run_reference_benchmark(
            repo_root=repo_root,
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            stage8_protocol_path=_resolve(
                repo_root,
                args.stage8_protocol,
            ),
            stage8_selection_root=_resolve(
                repo_root,
                args.stage8_selection_root,
            ),
            stage9_selection_root=_resolve(
                repo_root,
                args.stage9_selection_root,
            ),
            tumortwin_python=_resolve(
                repo_root,
                args.tumortwin_python,
            ),
            worker_script=_resolve(repo_root, args.worker_script),
            cache_root=_resolve(repo_root, args.cache_root),
            output_dir=_resolve(repo_root, args.output_dir),
            run_frozen=not args.calibrated_only,
            run_calibrated=not args.frozen_only,
            optimizer_iterations=args.optimizer_iterations,
            allow_dirty=args.allow_dirty,
            progress=lambda message: print(message, flush=True),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    summaries = artifact.manifest.get("summaries")
    if not isinstance(summaries, dict):
        print("Error: generated benchmark has no summaries", file=sys.stderr)
        return 1

    print()
    print(f"Reference benchmark created: {artifact.directory}")
    for engine, raw_summary in summaries.items():
        if not isinstance(raw_summary, dict):
            continue
        print(
            f"{engine}: mean Dice="
            f"{float(raw_summary['mean_dice']):.4f}; "
            f"delta vs persistence="
            f"{float(raw_summary['mean_delta_vs_persistence']):+.4f}; "
            f"delta vs Stage 9="
            f"{float(raw_summary['mean_delta_vs_stage9']):+.4f}; "
            f"catastrophic="
            f"{int(raw_summary['catastrophic_failure_count'])}"
        )
    return 0
