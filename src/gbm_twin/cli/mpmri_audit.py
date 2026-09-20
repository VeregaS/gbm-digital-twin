from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.mpmri_audit import audit_local_mpmri

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_AUDIT_ROOT = Path("results/cohort/stage8-data-audit-v1")
DEFAULT_OUTPUT_DIR = Path("results/cohort/mpmri-availability-v1")


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    data_audit_root: Path
    output_dir: Path


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit locally materialized CFB multimodal MRI without opening "
            "image contents or changing any validation split."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--data-audit-root",
        type=Path,
        default=DEFAULT_AUDIT_ROOT,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
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
        artifact = audit_local_mpmri(
            data_audit_root=_resolve(repo_root, args.data_audit_root),
            experiment_config_path=_resolve(
                repo_root,
                args.experiment_config,
            ),
            output_dir=_resolve(repo_root, args.output_dir),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    summary = artifact.manifest.get("summary")
    if not isinstance(summary, dict):
        print("Error: generated audit has no summary", file=sys.stderr)
        return 1

    print(f"mpMRI availability audit created: {artifact.directory}")
    print(f"Patients in audit: {int(summary['patient_count'])}")
    print(
        "Local patient directories: "
        f"{int(summary['local_patient_directory_count'])}"
    )
    print(
        "Longitudinal T1Gd + FLAIR: "
        f"{int(summary['longitudinal_t1gd_flair_count'])}"
    )
    print(
        "Longitudinal T1Gd + ADC: "
        f"{int(summary['longitudinal_t1gd_adc_count'])}"
    )
    print(
        "Longitudinal ADC: "
        f"{int(summary['longitudinal_adc_count'])}"
    )
    return 0
