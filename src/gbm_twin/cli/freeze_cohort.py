from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.cohort_freeze import (
    freeze_cohort_from_configs,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)

DEFAULT_DATASET_MANIFEST = Path(
    "configs/datasets/cfb_gbm_v4.yaml"
)


class CliArguments(argparse.Namespace):
    experiment_config: Path
    dataset_manifest: Path
    repo_root: Path
    cache_root: Path | None
    output_root: Path | None
    workers: int
    allow_dirty: bool


def _positive_int(
    value: str,
) -> int:
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
            "Freeze sealed V2 predictions "
            "for the selected cohort without "
            "revealing held-out t2 observations."
        ),
    )

    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
        help=(
            "Experiment YAML path relative "
            "to the repository root."
        ),
    )

    parser.add_argument(
        "--dataset-manifest",
        type=Path,
        default=DEFAULT_DATASET_MANIFEST,
        help=(
            "Pinned dataset manifest YAML "
            "relative to the repository root."
        ),
    )

    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help=(
            "Git repository root. "
            "Defaults to the current directory."
        ),
    )

    parser.add_argument(
        "--cache-root",
        type=Path,
        default=None,
        help=(
            "Calibration cache root. "
            "Defaults to results/cache/v2-cohort."
        ),
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help=(
            "Destination for the sealed cohort. "
            "Defaults to results/cohort/v2-freeze."
        ),
    )

    parser.add_argument(
        "--workers",
        type=_positive_int,
        default=1,
        help="Calibration worker count per patient.",
    )

    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "Allow freezing from a dirty Git "
            "working tree. Intended only for "
            "development runs."
        ),
    )

    return parser


def parse_arguments(
    argv: Sequence[str] | None = None,
) -> CliArguments:
    parser = build_parser()

    raw_argv = (
        None
        if argv is None
        else list(argv)
    )

    parsed = parser.parse_args(
        raw_argv,
        namespace=CliArguments(),
    )

    return cast(
        CliArguments,
        parsed,
    )


def _resolve_from_repo(
    repo_root: Path,
    path: Path,
) -> Path:
    if path.is_absolute():
        return path

    return repo_root / path


def _default_cache_root(
    repo_root: Path,
) -> Path:
    return (
        repo_root
        / "results"
        / "cache"
        / "v2-cohort"
    )


def _default_output_root(
    repo_root: Path,
) -> Path:
    return (
        repo_root
        / "results"
        / "cohort"
        / "v2-freeze"
    )


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_arguments(
        argv
    )

    repo_root = (
        args.repo_root.resolve()
    )

    experiment_config = (
        _resolve_from_repo(
            repo_root,
            args.experiment_config,
        )
    )

    dataset_manifest = (
        _resolve_from_repo(
            repo_root,
            args.dataset_manifest,
        )
    )

    if args.cache_root is None:
        cache_root = (
            _default_cache_root(
                repo_root
            )
        )
    else:
        cache_root = (
            _resolve_from_repo(
                repo_root,
                args.cache_root,
            )
        )

    if args.output_root is None:
        output_root = (
            _default_output_root(
                repo_root
            )
        )
    else:
        output_root = (
            _resolve_from_repo(
                repo_root,
                args.output_root,
            )
        )

    try:
        result = (
            freeze_cohort_from_configs(
                experiment_config_path=(
                    experiment_config
                ),
                dataset_manifest_path=(
                    dataset_manifest
                ),
                repo_root=repo_root,
                cache_root=cache_root,
                output_root=output_root,
                workers=args.workers,
                allow_dirty=(
                    args.allow_dirty
                ),
            )
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

    frozen_ids = (
        result.frozen_patient_ids
    )

    excluded_ids = (
        result.excluded_patient_ids
    )

    print(
        "Cohort V2 freeze created: "
        f"{result.directory}"
    )

    print(
        "Frozen patients: "
        f"{len(frozen_ids)}"
    )

    if frozen_ids:
        print(
            "  "
            + ", ".join(
                str(patient_id)
                for patient_id
                in frozen_ids
            )
        )

    print(
        "Excluded patients: "
        f"{len(excluded_ids)}"
    )

    for excluded in (
        result.manifest[
            "excluded_patients"
        ]
    ):
        reasons = ", ".join(
            issue["reason"]
            for issue
            in excluded["issues"]
        )

        print(
            "  "
            f"{excluded['patient_id']}: "
            f"{reasons}"
        )

    return 0