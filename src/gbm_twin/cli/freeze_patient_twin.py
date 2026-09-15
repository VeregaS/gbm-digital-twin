from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.patient_twin import (
    PatientNotEligibleError,
)
from gbm_twin.workflows.single_patient import (
    freeze_patient_from_configs,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)

DEFAULT_DATASET_MANIFEST = Path(
    "configs/datasets/cfb_gbm_v4.yaml"
)


class CliArguments(argparse.Namespace):
    patient_id: int
    experiment_config: Path
    dataset_manifest: Path
    repo_root: Path
    cache_dir: Path | None
    output_dir: Path | None
    workers: int


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
            "Freeze one held-out V2 GBM "
            "digital-twin prediction."
        ),
    )

    parser.add_argument(
        "patient_id",
        type=int,
        help=(
            "Patient ID selected by the "
            "experiment config."
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
        "--cache-dir",
        type=Path,
        default=None,
        help=(
            "Calibration cache directory. "
            "Defaults to a patient-specific "
            "directory under results/cache."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Frozen artifact directory. "
            "Defaults to a patient-specific "
            "directory under results/twin."
        ),
    )

    parser.add_argument(
        "--workers",
        type=_positive_int,
        default=1,
        help="Calibration worker count.",
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


def _default_cache_dir(
    *,
    repo_root: Path,
    patient_id: int,
) -> Path:
    return (
        repo_root
        / "results"
        / "cache"
        / "v2"
        / f"patient-{patient_id}"
    )


def _default_output_dir(
    *,
    repo_root: Path,
    patient_id: int,
) -> Path:
    return (
        repo_root
        / "results"
        / "twin"
        / f"patient-{patient_id}"
        / "frozen-v2"
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

    if args.cache_dir is None:
        cache_dir = _default_cache_dir(
            repo_root=repo_root,
            patient_id=args.patient_id,
        )
    else:
        cache_dir = _resolve_from_repo(
            repo_root,
            args.cache_dir,
        )

    if args.output_dir is None:
        output_dir = _default_output_dir(
            repo_root=repo_root,
            patient_id=args.patient_id,
        )
    else:
        output_dir = _resolve_from_repo(
            repo_root,
            args.output_dir,
        )

    try:
        artifact = (
            freeze_patient_from_configs(
                patient_id=args.patient_id,
                experiment_config_path=(
                    experiment_config
                ),
                dataset_manifest_path=(
                    dataset_manifest
                ),
                repo_root=repo_root,
                cache_dir=cache_dir,
                output_dir=output_dir,
                workers=args.workers,
            )
        )

    except PatientNotEligibleError as exc:
        print(
            (
                f"Patient "
                f"{exc.eligibility.patient_id} "
                "is not eligible:"
            ),
            file=sys.stderr,
        )

        for issue in (
            exc.eligibility.issues
        ):
            print(
                (
                    f"  - "
                    f"{issue.reason.value}: "
                    f"{issue.detail}"
                ),
                file=sys.stderr,
            )

        return 2

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
        
            "Frozen V2 prediction created: "
            f"{artifact.directory}"
        
    )

    return 0