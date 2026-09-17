from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.cohort_evaluation import (
    evaluate_frozen_cohort,
)
from gbm_twin.workflows.cohort_results import (
    summarize_cohort_evaluation,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)
DEFAULT_COHORT_DIR = Path(
    "results/cohort/v2-freeze"
)
DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/v2-evaluation"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    cohort_dir: Path
    output_dir: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Reveal held-out t2 observations and evaluate an already "
            "sealed cohort freeze. All prediction artifacts are validated "
            "before the first t2 observation is loaded."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--cohort-dir",
        type=Path,
        default=DEFAULT_COHORT_DIR,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    return parser


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> CliArguments:
    return cast(
        CliArguments,
        build_parser().parse_args(
            None if argv is None else list(argv),
            namespace=CliArguments(),
        ),
    )


def _resolve(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return repo_root / path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    repo_root = args.repo_root.resolve()

    try:
        result = evaluate_frozen_cohort(
            cohort_dir=_resolve(
                repo_root,
                args.cohort_dir,
            ),
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            output_dir=_resolve(
                repo_root,
                args.output_dir,
            ),
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    summary = summarize_cohort_evaluation(
        result.manifest
    )
    model_version = result.manifest.get(
        "model_version",
        "V2",
    )

    print(
        f"Cohort {model_version} evaluation created: "
        f"{result.directory}"
    )
    print(f"Evaluated patients: {summary.patient_count}")

    if summary.twin.mean_dice is not None:
        print(
            "Twin mean Dice: "
            f"{summary.twin.mean_dice:.4f}"
        )
    if summary.persistence.mean_dice is not None:
        print(
            "Persistence mean Dice: "
            f"{summary.persistence.mean_dice:.4f}"
        )

    print(
        "Twin vs persistence: "
        f"{summary.twin_better_than_persistence_count} better, "
        f"{summary.twin_equal_to_persistence_count} equal, "
        f"{summary.twin_worse_than_persistence_count} worse"
    )
    return 0
