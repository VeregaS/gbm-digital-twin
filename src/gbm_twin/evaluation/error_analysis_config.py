from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml


@dataclass(frozen=True)
class CohortErrorAnalysisConfig:
    stable_volume_change_fraction: float
    worst_patient_count: int
    min_correlation_patients: int


def _require_mapping(
    value: object,
    name: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _require_int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(key)

    if type(value) is not int:
        raise ValueError(
            f"{key} must be an integer"
        )

    return cast(int, value)


def _require_float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(key)

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"{key} must be numeric"
        )

    return float(value)


def load_cohort_error_analysis_config(
    path: Path,
) -> CohortErrorAnalysisConfig:
    if not path.is_file():
        raise FileNotFoundError(
            f"Analysis config not found: {path}"
        )

    raw: object

    with path.open(
        "r",
        encoding="utf-8",
    ) as stream:
        raw = yaml.safe_load(stream)

    root = _require_mapping(
        raw,
        "analysis config",
    )

    schema_version = _require_int(
        root,
        "schema_version",
    )

    if schema_version != 1:
        raise ValueError(
            "Unsupported cohort error analysis config schema version"
        )

    stable_threshold = _require_float(
        root,
        "stable_volume_change_fraction",
    )

    worst_patient_count = _require_int(
        root,
        "worst_patient_count",
    )

    min_correlation_patients = _require_int(
        root,
        "min_correlation_patients",
    )

    if stable_threshold < 0.0:
        raise ValueError(
            "stable_volume_change_fraction must be non-negative"
        )

    if worst_patient_count < 1:
        raise ValueError(
            "worst_patient_count must be positive"
        )

    if min_correlation_patients < 2:
        raise ValueError(
            "min_correlation_patients must be at least 2"
        )

    return CohortErrorAnalysisConfig(
        stable_volume_change_fraction=stable_threshold,
        worst_patient_count=worst_patient_count,
        min_correlation_patients=min_correlation_patients,
    )
