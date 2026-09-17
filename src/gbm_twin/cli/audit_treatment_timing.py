from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.workflows.treatment_timing import (
    build_treatment_timing_audit,
)

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)

DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/treatment-timing-audit"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    output_dir: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit reconstructed radiotherapy timing at t1 without "
            "loading or using t2 observations."
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


def main(
    argv: Sequence[str] | None = None,
) -> int:
    args = parse_arguments(argv)

    try:
        result = build_treatment_timing_audit(
            repo_root=args.repo_root,
            experiment_config_path=(
                args.experiment_config
            ),
            output_dir=args.output_dir,
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
        "Treatment timing audit created: "
        f"{result.directory}"
    )
    print(
        "Patients: "
        f"{result.summary['patient_count']}"
    )
    print(
        "Reconstructable RT: "
        f"{result.summary['treatment_reconstructable_count']}"
    )
    print(
        "RT completed by t1: "
        f"{result.summary['rt_completed_by_t1_count']}"
    )
    print(
        "Patients with fractions after t1: "
        f"{result.summary['patients_with_future_rt_fractions_count']}"
    )

    print("Patient timing:")

    for record in result.records:
        if not record.treatment_reconstructable:
            print(
                f"  {record.patient_id}: RT schedule unavailable"
            )
            continue

        print(
            "  "
            f"{record.patient_id}: "
            f"t1={record.t1_day}, "
            f"last_fraction={record.last_fraction_day}, "
            f"completed_by_t1={record.rt_completed_by_t1}, "
            f"fractions_after_t1={record.fractions_after_t1}, "
            "days_last_fraction_to_t1="
            f"{record.days_from_last_fraction_to_t1}"
        )

    return 0
