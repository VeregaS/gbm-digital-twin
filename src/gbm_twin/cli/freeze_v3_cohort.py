from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.cohort_freeze import (
    freeze_v3_cohort_from_configs,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_DATASET_MANIFEST = Path(
    "configs/datasets/cfb_gbm_v4.yaml"
)
DEFAULT_SELECTION_ROOT = Path(
    "results/cohort/v3-post-rt-selection"
)
DEFAULT_CACHE_ROOT = Path(
    "results/cache/v3-post-rt"
)
DEFAULT_OUTPUT_ROOT = Path(
    "results/cohort/v3-freeze"
)


class CliArguments(argparse.Namespace):
    experiment_config: Path
    dataset_manifest: Path
    selection_root: Path
    repo_root: Path
    cache_root: Path
    output_root: Path
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
            "Freeze sealed V3 post-radiotherapy predictions for the "
            "selected cohort without revealing held-out t2 observations."
        )
    )
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=DEFAULT_DATASET_MANIFEST,
    )
    parser.add_argument(
        "--selection-root",
        type=Path,
        default=DEFAULT_SELECTION_ROOT,
        help=(
            "Directory containing the sealed pre-t2 "
            "post_rt_selection.json artifact."
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=DEFAULT_CACHE_ROOT,
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )
    parser.add_argument(
        "--workers",
        type=_positive_int,
        default=1,
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "Allow freezing from a dirty Git working tree. "
            "Intended only for development runs."
        ),
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
        result = freeze_v3_cohort_from_configs(
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            dataset_manifest_path=_resolve(
                repo_root,
                args.dataset_manifest,
            ),
            post_rt_selection_root=_resolve(
                repo_root,
                args.selection_root,
            ),
            repo_root=repo_root,
            cache_root=_resolve(
                repo_root,
                args.cache_root,
            ),
            output_root=_resolve(
                repo_root,
                args.output_root,
            ),
            workers=args.workers,
            allow_dirty=args.allow_dirty,
        )
    except (
        OSError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    model = result.manifest.get("model")
    print(f"Cohort V3 freeze created: {result.directory}")
    print(f"Frozen patients: {len(result.frozen_patient_ids)}")
    if result.frozen_patient_ids:
        print(
            "  "
            + ", ".join(
                str(patient_id)
                for patient_id in result.frozen_patient_ids
            )
        )

    print(f"Excluded patients: {len(result.excluded_patient_ids)}")
    for excluded in result.manifest["excluded_patients"]:
        reasons = ", ".join(
            issue["reason"]
            for issue in excluded["issues"]
        )
        print(f"  {excluded['patient_id']}: {reasons}")

    if model is not None:
        print(
            "V3 post-RT candidate: "
            f"{model['post_rt_candidate_id']} "
            f"(k0={model['post_rt_initial_kill_rate_per_day']}, "
            f"tau={model['post_rt_decay_time_days']} d)"
        )

    return 0
