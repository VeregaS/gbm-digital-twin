from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import cast

from gbm_twin.evaluation.experiment_comparison import (
    AccuracyExperimentComparison,
    compare_cohort_analyses,
)
from gbm_twin.workflows.cohort_analysis import (
    load_sealed_cohort_analysis,
)

DEFAULT_BASELINE_ANALYSIS = Path(
    "results/cohort/v2-analysis"
)
DEFAULT_CANDIDATE_ANALYSIS = Path(
    "results/cohort/v2-accuracy-v1-analysis"
)
DEFAULT_OUTPUT_CSV = Path(
    "results/cohort/v2-accuracy-v1-comparison.csv"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    baseline_analysis: Path
    candidate_analysis: Path
    output_csv: Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two sealed cohort scientific-analysis artifacts "
            "patient by patient, including different model versions."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--baseline-analysis",
        type=Path,
        default=DEFAULT_BASELINE_ANALYSIS,
    )
    parser.add_argument(
        "--candidate-analysis",
        type=Path,
        default=DEFAULT_CANDIDATE_ANALYSIS,
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
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


def _write_csv(
    path: Path,
    comparison: AccuracyExperimentComparison,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "patient_id",
        "baseline_twin_dice",
        "candidate_twin_dice",
        "twin_dice_delta",
        "baseline_delta_vs_persistence",
        "candidate_delta_vs_persistence",
        "delta_vs_persistence_change",
        "baseline_calibration_dice",
        "candidate_calibration_dice",
        "calibration_dice_delta",
        "baseline_diffusion",
        "candidate_diffusion",
        "baseline_proliferation",
        "candidate_proliferation",
        "baseline_calibration_identifiable",
        "candidate_calibration_identifiable",
        "baseline_diffusion_at_boundary",
        "candidate_diffusion_at_boundary",
        "baseline_proliferation_at_boundary",
        "candidate_proliferation_at_boundary",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        for patient in comparison.patients:
            row = asdict(patient)
            writer.writerow(
                {field: row[field] for field in fieldnames}
            )


def _analysis_label(manifest: dict[str, object]) -> str:
    model = manifest.get("model_version")
    if model == "V3":
        return "V3"

    kind = manifest.get("kind")
    if kind == "v2_cohort_error_analysis":
        return "V2"

    return str(kind)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_arguments(argv)
    repo_root = args.repo_root.resolve()

    try:
        baseline = load_sealed_cohort_analysis(
            _resolve(repo_root, args.baseline_analysis)
        )
        candidate = load_sealed_cohort_analysis(
            _resolve(repo_root, args.candidate_analysis)
        )
        comparison = compare_cohort_analyses(
            baseline.manifest,
            candidate.manifest,
        )
        output_csv = _resolve(
            repo_root,
            args.output_csv,
        )
        _write_csv(output_csv, comparison)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        "Cohort accuracy comparison: "
        f"{_analysis_label(baseline.manifest)} -> "
        f"{_analysis_label(candidate.manifest)}"
    )
    print(f"Patients: {comparison.patient_count}")
    print(
        "Mean Twin Dice change: "
        f"{comparison.mean_twin_dice_delta:+.4f}"
    )
    print(
        "Median Twin Dice change: "
        f"{comparison.median_twin_dice_delta:+.4f}"
    )
    print(
        "Patients: "
        f"{comparison.improved_patient_count} improved, "
        f"{comparison.equal_patient_count} equal, "
        f"{comparison.degraded_patient_count} degraded"
    )
    print(
        "Mean change in Twin-vs-persistence Dice delta: "
        f"{comparison.mean_delta_vs_persistence_change:+.4f}"
    )
    print(
        "Boundary calibrations: "
        f"{comparison.baseline_boundary_patient_count} -> "
        f"{comparison.candidate_boundary_patient_count}"
    )
    print(
        "Non-identifiable calibrations: "
        f"{comparison.baseline_non_identifiable_count} -> "
        f"{comparison.candidate_non_identifiable_count}"
    )
    print("Patient deltas:")
    for patient in comparison.patients:
        print(
            "  "
            f"{patient.patient_id}: "
            f"Dice {patient.baseline_twin_dice:.4f} -> "
            f"{patient.candidate_twin_dice:.4f} "
            f"({patient.twin_dice_delta:+.4f}), "
            f"D {patient.baseline_diffusion:.5f} -> "
            f"{patient.candidate_diffusion:.5f}, "
            f"rho {patient.baseline_proliferation:.5f} -> "
            f"{patient.candidate_proliferation:.5f}"
        )
    print(f"CSV: {output_csv}")
    return 0
