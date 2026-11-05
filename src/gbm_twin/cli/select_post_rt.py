from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.post_rt_selection import (
    select_post_rt_parameters,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_SELECTION_CONFIG = Path(
    "configs/research/post_rt_selection_v1.yaml"
)
DEFAULT_CACHE_ROOT = Path(
    "results/cache/v3-post-rt-selection"
)
DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/v3-post-rt-selection"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    selection_config: Path
    cache_root: Path
    output_dir: Path
    workers: int
    allow_dirty: bool


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "value must be an integer"
        ) from exc

    if parsed < 1:
        raise argparse.ArgumentTypeError(
            "value must be at least 1"
        )

    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Select a global delayed post-RT treatment candidate using only "
            "t0 -> t1 calibration data. The workflow does not load t2."
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
        "--selection-config",
        type=Path,
        default=DEFAULT_SELECTION_CONFIG,
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
    parser.add_argument(
        "--workers",
        type=_positive_int,
        default=1,
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
    )

    return parser


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> CliArguments:
    parsed = build_parser().parse_args(
        None if argv is None else list(argv),
        namespace=CliArguments(),
    )

    return cast(
        CliArguments,
        parsed,
    )


def _resolve(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path

    return repo_root / path


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_arguments(argv)
    repo_root = args.repo_root.resolve()

    try:
        result = select_post_rt_parameters(
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            selection_config_path=_resolve(
                repo_root,
                args.selection_config,
            ),
            repo_root=repo_root,
            cache_root=_resolve(
                repo_root,
                args.cache_root,
            ),
            output_dir=_resolve(
                repo_root,
                args.output_dir,
            ),
            workers=args.workers,
            allow_dirty=args.allow_dirty,
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

    selected = result.manifest.get(
        "selected_candidate"
    )

    print(
        "Post-RT parameter selection created: "
        f"{result.directory}"
    )
    print(
        "Selection used t0 -> t1 only; t2 imaging was not loaded."
    )
    print(
        "Selected candidate: "
        f"{selected}"
    )
    print(
        "Artifacts: post_rt_selection.json, post_rt_selection.sha256, "
        "post_rt_candidates.csv, post_rt_patients.csv"
    )

    return 0
