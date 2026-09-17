from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)
from gbm_twin.workflows.cohort_analysis import (
    analyze_sealed_cohort,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)

DEFAULT_ANALYSIS_CONFIG = Path(
    "configs/analysis/cohort_error_analysis.yaml"
)

DEFAULT_COHORT_FREEZE_ROOT = Path(
    "results/cohort/v2-freeze"
)

DEFAULT_COHORT_EVALUATION_ROOT = Path(
    "results/cohort/v2-evaluation"
)

DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/v2-analysis"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    analysis_config: Path
    cohort_freeze_root: Path
    cohort_evaluation_root: Path
    output_dir: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a sealed scientific error-analysis artifact from an "
            "already sealed V2 cohort evaluation."
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
        "--analysis-config",
        type=Path,
        default=DEFAULT_ANALYSIS_CONFIG,
    )

    parser.add_argument(
        "--cohort-freeze-root",
        type=Path,
        default=DEFAULT_COHORT_FREEZE_ROOT,
    )

    parser.add_argument(
        "--cohort-evaluation-root",
        type=Path,
        default=DEFAULT_COHORT_EVALUATION_ROOT,
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


def _resolve(
    repo_root: Path,
    path: Path,
) -> Path:
    if path.is_absolute():
        return path

    return repo_root / path


def _summary_float(
    summary: dict[str, object],
    key: str,
) -> float | None:
    value = summary.get(key)

    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"Analysis summary field {key!r} must be numeric"
        )

    return float(value)


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_arguments(argv)
    repo_root = args.repo_root.resolve()

    experiment_config_path = _resolve(
        repo_root,
        args.experiment_config,
    )

    try:
        experiment = load_cohort_experiment_config(
            experiment_config_path
        )

        result = analyze_sealed_cohort(
            metadata_root=_resolve(
                repo_root,
                experiment.metadata_root,
            ),
            patients_root=_resolve(
                repo_root,
                experiment.patients_root,
            ),
            cohort_freeze_root=_resolve(
                repo_root,
                args.cohort_freeze_root,
            ),
            cohort_evaluation_root=_resolve(
                repo_root,
                args.cohort_evaluation_root,
            ),
            analysis_config_path=_resolve(
                repo_root,
                args.analysis_config,
            ),
            output_dir=_resolve(
                repo_root,
                args.output_dir,
            ),
        )

        raw_summary = result.manifest.get(
            "summary"
        )

        if not isinstance(raw_summary, dict):
            raise ValueError(
                "Generated analysis summary is missing"
            )

        summary = cast(
            dict[str, object],
            raw_summary,
        )

        mean_dice = _summary_float(
            summary,
            "mean_twin_dice",
        )

        mean_delta = _summary_float(
            summary,
            "mean_delta_vs_persistence",
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

    print(
        "Cohort scientific analysis created: "
        f"{result.directory}"
    )

    if mean_dice is not None:
        print(
            "Twin mean Dice: "
            f"{mean_dice:.4f}"
        )

    if mean_delta is not None:
        print(
            "Mean Dice delta vs persistence: "
            f"{mean_delta:+.4f}"
        )

    print(
        "Artifacts: cohort_analysis.json, "
        "cohort_analysis.sha256, cohort_analysis.csv"
    )

    return 0
