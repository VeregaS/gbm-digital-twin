from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from gbm_twin.workflows.cohort_evaluation import (
    COHORT_EVALUATION_SCHEMA_VERSION,
    CohortEvaluationPayload,
    CohortEvaluationResult,
    MethodMetricsPayload,
    PatientEvaluationPayload,
    SourceArtifactPayload,
    SourceDatasetPayload,
    SourceRepositoryPayload,
)
from gbm_twin.workflows.provenance import sha256_file

_SHA256_PATTERN = re.compile(
    r"^[0-9a-f]{64}$"
)

MethodName = Literal[
    "twin",
    "persistence",
    "volume_baseline",
]


@dataclass(frozen=True)
class CohortMethodSummary:
    patient_count: int

    hd95_count: int
    centroid_distance_count: int

    mean_dice: float | None
    mean_relative_volume_error: float | None
    mean_hd95_mm: float | None
    mean_centroid_distance_mm: float | None


@dataclass(frozen=True)
class CohortEvaluationSummary:
    patient_count: int

    twin: CohortMethodSummary
    persistence: CohortMethodSummary
    volume_baseline: CohortMethodSummary

    twin_better_than_persistence_count: int
    twin_equal_to_persistence_count: int
    twin_worse_than_persistence_count: int


def _require_mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            f"Field {key!r} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _require_list(
    mapping: dict[str, object],
    key: str,
) -> list[object]:
    value = mapping.get(key)

    if not isinstance(value, list):
        raise ValueError(
            f"Field {key!r} must be a list"
        )

    return cast(
        list[object],
        value,
    )


def _require_string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str):
        raise ValueError(
            f"Field {key!r} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"Field {key!r} must not be empty"
        )

    return normalized


def _require_sha256(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = _require_string(
        mapping,
        key,
    )

    if (
        _SHA256_PATTERN.fullmatch(value)
        is None
    ):
        raise ValueError(
            f"Field {key!r} must be SHA-256"
        )

    return value


def _require_int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(key)

    if type(value) is not int:
        raise ValueError(
            f"Field {key!r} must be an integer"
        )

    return cast(
        int,
        value,
    )


def _require_bool(
    mapping: dict[str, object],
    key: str,
) -> bool:
    value = mapping.get(key)

    if type(value) is not bool:
        raise ValueError(
            f"Field {key!r} must be a boolean"
        )

    return cast(
        bool,
        value,
    )


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
            f"Field {key!r} must be numeric"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            f"Field {key!r} must be finite"
        )

    return result


def _require_nonnegative_float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = _require_float(
        mapping,
        key,
    )

    if value < 0.0:
        raise ValueError(
            f"Field {key!r} must be non-negative"
        )

    return value


def _require_optional_nonnegative_float(
    mapping: dict[str, object],
    key: str,
) -> float | None:
    raw = mapping.get(key)

    if raw is None:
        return None

    return _require_nonnegative_float(
        mapping,
        key,
    )


def _require_spacing(
    mapping: dict[str, object],
    key: str,
) -> list[float]:
    values = _require_list(
        mapping,
        key,
    )

    if len(values) != 3:
        raise ValueError(
            f"Field {key!r} must contain three values"
        )

    result: list[float] = []

    for raw in values:
        if (
            isinstance(raw, bool)
            or not isinstance(
                raw,
                (int, float),
            )
        ):
            raise ValueError(
                f"Field {key!r} must contain numbers"
            )

        value = float(raw)

        if (
            not math.isfinite(value)
            or value <= 0.0
        ):
            raise ValueError(
                f"Field {key!r} must contain "
                "finite positive values"
            )

        result.append(value)

    return result


def _parse_method(
    raw: object,
) -> MethodMetricsPayload:
    if not isinstance(raw, dict):
        raise ValueError(
            "Method metrics must be a mapping"
        )

    mapping = cast(
        dict[str, object],
        raw,
    )

    dice = _require_float(
        mapping,
        "dice",
    )

    if not 0.0 <= dice <= 1.0:
        raise ValueError(
            "Dice must be within [0, 1]"
        )

    return {
        "dice": dice,
        "relative_volume_error": (
            _require_nonnegative_float(
                mapping,
                "relative_volume_error",
            )
        ),
        "hd95_mm": (
            _require_optional_nonnegative_float(
                mapping,
                "hd95_mm",
            )
        ),
        "centroid_distance_mm": (
            _require_optional_nonnegative_float(
                mapping,
                "centroid_distance_mm",
            )
        ),
    }


def _parse_patient(
    raw: object,
) -> PatientEvaluationPayload:
    if not isinstance(raw, dict):
        raise ValueError(
            "Patient evaluation must be a mapping"
        )

    mapping = cast(
        dict[str, object],
        raw,
    )

    return {
        "patient_id": _require_int(
            mapping,
            "patient_id",
        ),
        "target_timepoint": _require_string(
            mapping,
            "target_timepoint",
        ),
        "target_day": _require_float(
            mapping,
            "target_day",
        ),
        "twin": _parse_method(
            mapping.get("twin")
        ),
        "persistence": _parse_method(
            mapping.get("persistence")
        ),
        "volume_baseline": _parse_method(
            mapping.get("volume_baseline")
        ),
    }


def load_sealed_cohort_evaluation(
    directory: Path,
) -> CohortEvaluationResult:
    root = directory.resolve()

    manifest_path = (
        root
        / "cohort_evaluation.json"
    )

    seal_path = (
        root
        / "cohort_evaluation.sha256"
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Cohort evaluation manifest "
            f"not found: {manifest_path}"
        )

    if not seal_path.is_file():
        raise FileNotFoundError(
            "Cohort evaluation seal "
            f"not found: {seal_path}"
        )

    seal_tokens = seal_path.read_text(
        encoding="ascii"
    ).split()

    if not seal_tokens:
        raise ValueError(
            "Cohort evaluation seal is empty"
        )

    expected_sha256 = seal_tokens[0]

    actual_sha256 = sha256_file(
        manifest_path
    )

    if (
        actual_sha256
        != expected_sha256
    ):
        raise ValueError(
            "Cohort evaluation checksum mismatch"
        )

    raw: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(raw, dict):
        raise ValueError(
            "Cohort evaluation must "
            "contain a JSON object"
        )

    root_payload = cast(
        dict[str, object],
        raw,
    )

    schema_version = _require_int(
        root_payload,
        "schema_version",
    )

    if (
        schema_version
        != COHORT_EVALUATION_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported cohort evaluation "
            "schema version"
        )

    if (
        _require_string(
            root_payload,
            "kind",
        )
        != "v2_cohort_evaluation"
    ):
        raise ValueError(
            "Artifact is not a V2 "
            "cohort evaluation"
        )

    if not _require_bool(
        root_payload,
        "sealed",
    ):
        raise ValueError(
            "Cohort evaluation is not sealed"
        )

    dataset_raw = _require_mapping(
        root_payload,
        "dataset",
    )

    repository_raw = _require_mapping(
        root_payload,
        "repository",
    )

    dataset: SourceDatasetPayload = {
        "name": _require_string(
            dataset_raw,
            "name",
        ),
        "version": _require_int(
            dataset_raw,
            "version",
        ),
        "doi": _require_string(
            dataset_raw,
            "doi",
        ),
    }

    repository: SourceRepositoryPayload = {
        "commit_sha": _require_string(
            repository_raw,
            "commit_sha",
        ),
        "dirty": _require_bool(
            repository_raw,
            "dirty",
        ),
    }

    source_artifacts: list[
        SourceArtifactPayload
    ] = []

    for raw_artifact in _require_list(
        root_payload,
        "source_artifacts",
    ):
        if not isinstance(
            raw_artifact,
            dict,
        ):
            raise ValueError(
                "Source artifact entry "
                "must be a mapping"
            )

        artifact = cast(
            dict[str, object],
            raw_artifact,
        )

        source_artifacts.append(
            {
                "patient_id": _require_int(
                    artifact,
                    "patient_id",
                ),
                "artifact_dir": (
                    _require_string(
                        artifact,
                        "artifact_dir",
                    )
                ),
                "manifest_sha256": (
                    _require_sha256(
                        artifact,
                        "manifest_sha256",
                    )
                ),
            }
        )

    patients = [
        _parse_patient(raw_patient)
        for raw_patient in _require_list(
            root_payload,
            "patients",
        )
    ]

    patient_ids = [
        patient["patient_id"]
        for patient in patients
    ]

    if (
        len(patient_ids)
        != len(set(patient_ids))
    ):
        raise ValueError(
            "Cohort evaluation contains "
            "duplicate patients"
        )

    payload: CohortEvaluationPayload = {
        "schema_version": (
            COHORT_EVALUATION_SCHEMA_VERSION
        ),
        "kind": "v2_cohort_evaluation",
        "sealed": True,
        "source_freeze_manifest_sha256": (
            _require_sha256(
                root_payload,
                "source_freeze_manifest_sha256",
            )
        ),
        "dataset": dataset,
        "repository": repository,
        "target_spacing": _require_spacing(
            root_payload,
            "target_spacing",
        ),
        "source_artifacts": (
            source_artifacts
        ),
        "patients": patients,
    }

    return CohortEvaluationResult(
        directory=root,
        manifest=payload,
    )


def _mean(
    values: Sequence[float],
) -> float | None:
    if not values:
        return None

    return (
        sum(values)
        / len(values)
    )


def _method_summary(
    patients: Sequence[
        PatientEvaluationPayload
    ],
    method: MethodName,
) -> CohortMethodSummary:
    metrics = [
        patient[method]
        for patient in patients
    ]

    hd95_values = [
        value
        for metric in metrics
        if (
            value := metric["hd95_mm"]
        )
        is not None
    ]

    centroid_values = [
        value
        for metric in metrics
        if (
            value
            := metric[
                "centroid_distance_mm"
            ]
        )
        is not None
    ]

    return CohortMethodSummary(
        patient_count=len(metrics),
        hd95_count=len(
            hd95_values
        ),
        centroid_distance_count=len(
            centroid_values
        ),
        mean_dice=_mean(
            [
                metric["dice"]
                for metric in metrics
            ]
        ),
        mean_relative_volume_error=(
            _mean(
                [
                    metric[
                        "relative_volume_error"
                    ]
                    for metric in metrics
                ]
            )
        ),
        mean_hd95_mm=_mean(
            hd95_values
        ),
        mean_centroid_distance_mm=(
            _mean(
                centroid_values
            )
        ),
    )


def summarize_cohort_evaluation(
    payload: CohortEvaluationPayload,
) -> CohortEvaluationSummary:
    patients = payload["patients"]

    better = 0
    equal = 0
    worse = 0

    for patient in patients:
        twin_dice = (
            patient["twin"]["dice"]
        )

        persistence_dice = (
            patient[
                "persistence"
            ]["dice"]
        )

        if math.isclose(
            twin_dice,
            persistence_dice,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            equal += 1
        elif (
            twin_dice
            > persistence_dice
        ):
            better += 1
        else:
            worse += 1

    return CohortEvaluationSummary(
        patient_count=len(patients),
        twin=_method_summary(
            patients,
            "twin",
        ),
        persistence=_method_summary(
            patients,
            "persistence",
        ),
        volume_baseline=_method_summary(
            patients,
            "volume_baseline",
        ),
        twin_better_than_persistence_count=(
            better
        ),
        twin_equal_to_persistence_count=(
            equal
        ),
        twin_worse_than_persistence_count=(
            worse
        ),
    )