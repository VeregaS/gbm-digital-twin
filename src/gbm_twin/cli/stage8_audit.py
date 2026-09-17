from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.workflows.stage8_data_audit import audit_stage8_cohort

DEFAULT_EXPERIMENT_CONFIG = Path(
    "configs/experiments/mini_cohort_accuracy_v1.yaml"
)
DEFAULT_PROTOCOL_CONFIG = Path(
    "configs/research/stage8_protocol.yaml"
)
DEFAULT_OUTPUT_DIR = Path(
    "results/cohort/stage8-data-audit"
)


class CliArguments(argparse.Namespace):
    repo_root: Path
    experiment_config: Path
    protocol_config: Path
    metadata_root: Path | None
    output_dir: Path


def _resolve(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return repo_root / path


def _role_counts(patients: object) -> tuple[int, int]:
    if not isinstance(patients, list):
        raise ValueError("Generated Stage 8 audit is missing patient rows")

    exposed = 0
    internal_validation = 0
    for raw in patients:
        if not isinstance(raw, dict):
            continue
        if raw.get("core_eligible") is not True:
            continue
        if raw.get("split") == "development-exposed":
            exposed += 1
        elif raw.get("split") in {"development", "internal-validation"}:
            internal_validation += 1
    return exposed, internal_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build the leakage-safe Stage 8 CFB multimodal/RTDOSE audit "
            "and deterministic development/validation/holdout roles."
        )
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--experiment-config",
        type=Path,
        default=DEFAULT_EXPERIMENT_CONFIG,
    )
    parser.add_argument(
        "--protocol-config",
        type=Path,
        default=DEFAULT_PROTOCOL_CONFIG,
    )
    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=None,
        help=(
            "Override CFB metadata root. By default it is read from the "
            "existing experiment config."
        ),
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
        experiment_path = _resolve(repo_root, args.experiment_config)
        experiment = load_cohort_experiment_config(experiment_path)
        metadata_root = (
            args.metadata_root.resolve()
            if args.metadata_root is not None
            else _resolve(repo_root, experiment.metadata_root).resolve()
        )
        result = audit_stage8_cohort(
            metadata_root=metadata_root,
            protocol_config_path=_resolve(repo_root, args.protocol_config),
            output_dir=_resolve(repo_root, args.output_dir),
        )
        raw_summary = result.manifest.get("summary")
        raw_split = result.manifest.get("split")
        if not isinstance(raw_summary, dict) or not isinstance(raw_split, dict):
            raise ValueError("Generated Stage 8 audit is missing summary data")
        exposed_count, validation_count = _role_counts(
            result.manifest.get("patients")
        )
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Stage 8 data audit created: {result.directory}")
    print(
        "Leakage contract: availability/treatment metadata only; "
        "RANO and t2 image content were not loaded."
    )
    print(
        "Patients: "
        f"{raw_summary.get('patient_count')}; "
        f"core eligible: {raw_summary.get('core_eligible_count')}"
    )
    print(
        "Cohort roles: "
        f"development-exposed={exposed_count}; "
        f"internal-validation={validation_count}; "
        f"untouched-holdout={raw_summary.get('untouched_holdout_count')}"
    )
    print(
        "Rich inputs: "
        f"FLAIR t0/t1={raw_summary.get('flair_t0_t1_complete_count')}, "
        f"DWI/ADC t0/t1={raw_summary.get('dwi_t0_t1_complete_count')}, "
        f"RTDOSE={raw_summary.get('rtdose_available_count')}"
    )
    print(
        "Model tiers: "
        + json.dumps(
            raw_summary.get("model_tier_counts", {}),
            sort_keys=True,
        )
    )
    print(
        "Untouched holdout IDs: "
        + ", ".join(
            str(value)
            for value in raw_split.get("untouched_holdout_patient_ids", [])
        )
    )
    print(
        "Artifacts: stage8_data_audit.json, stage8_data_audit.sha256, "
        "stage8_data_audit.csv"
    )
    return 0
