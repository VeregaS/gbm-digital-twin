from __future__ import annotations

import json
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from gbm_twin.evaluation.config import (
    CohortExperimentConfig,
    load_cohort_experiment_config,
)
from gbm_twin.evaluation.frozen_prediction import (
    FrozenV2EvaluationResult,
    evaluate_frozen_v2_prediction,
)
from gbm_twin.workflows.cohort_freeze import (
    COHORT_FREEZE_SCHEMA_VERSION,
)
from gbm_twin.workflows.patients import (
    prepare_patient_timepoint,
)
from gbm_twin.workflows.prediction import (
    load_frozen_v2_prediction,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)

COHORT_EVALUATION_SCHEMA_VERSION = 1


class MethodMetricsPayload(TypedDict):
    dice: float
    relative_volume_error: float
    hd95_mm: float | None
    centroid_distance_mm: float | None


class PatientEvaluationPayload(TypedDict):
    patient_id: int
    target_timepoint: str
    target_day: float
    twin: MethodMetricsPayload
    persistence: MethodMetricsPayload
    volume_baseline: MethodMetricsPayload


class SourceDatasetPayload(TypedDict):
    name: str
    version: int
    doi: str


class SourceRepositoryPayload(TypedDict):
    commit_sha: str
    dirty: bool


class SourceArtifactPayload(TypedDict):
    patient_id: int
    artifact_dir: str
    manifest_sha256: str


class CohortEvaluationPayload(TypedDict):
    schema_version: int
    kind: str
    sealed: bool
    source_freeze_manifest_sha256: str
    dataset: SourceDatasetPayload
    repository: SourceRepositoryPayload
    target_spacing: list[float]
    source_artifacts: list[SourceArtifactPayload]
    patients: list[PatientEvaluationPayload]


@dataclass(frozen=True)
class CohortEvaluationResult:
    directory: Path
    manifest: CohortEvaluationPayload

    @property
    def evaluated_patient_ids(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            patient["patient_id"]
            for patient in self.manifest["patients"]
        )


@dataclass(frozen=True)
class _FrozenPatientReference:
    patient_id: int
    artifact_dir: str


@dataclass(frozen=True)
class _SourceFreeze:
    manifest_sha256: str

    dataset_name: str
    dataset_version: int
    dataset_doi: str

    repository_commit_sha: str
    repository_dirty: bool

    experiment_config_file: str

    target_spacing: tuple[
        float,
        float,
        float,
    ]

    frozen_patients: tuple[
        _FrozenPatientReference,
        ...,
    ]


@dataclass(frozen=True)
class _ValidatedArtifact:
    patient_id: int
    artifact_dir: Path
    relative_artifact_dir: str
    manifest_sha256: str


def _require_mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        dict,
    ):
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
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        list,
    ):
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
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            f"Field {key!r} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"Field {key!r} must not be empty"
        )

    return normalized


def _require_int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(
        key
    )

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
    value = mapping.get(
        key
    )

    if type(value) is not bool:
        raise ValueError(
            f"Field {key!r} must be a boolean"
        )

    return cast(
        bool,
        value,
    )


def _require_spacing(
    mapping: dict[str, object],
    key: str,
) -> tuple[
    float,
    float,
    float,
]:
    raw_values = _require_list(
        mapping,
        key,
    )

    if len(raw_values) != 3:
        raise ValueError(
            f"Field {key!r} must contain three values"
        )

    values: list[float] = []

    for raw_value in raw_values:
        if (
            isinstance(
                raw_value,
                bool,
            )
            or not isinstance(
                raw_value,
                (int, float),
            )
        ):
            raise ValueError(
                f"Field {key!r} must contain numbers"
            )

        value = float(
            raw_value
        )

        if (
            not math.isfinite(
                value
            )
            or value <= 0.0
        ):
            raise ValueError(
                f"Field {key!r} must contain "
                "finite positive values"
            )

        values.append(
            value
        )

    return (
        values[0],
        values[1],
        values[2],
    )


def _read_sealed_json(
    *,
    json_path: Path,
    seal_path: Path,
) -> tuple[
    dict[str, object],
    str,
]:
    if not json_path.is_file():
        raise FileNotFoundError(
            f"JSON artifact not found: {json_path}"
        )

    if not seal_path.is_file():
        raise FileNotFoundError(
            f"Artifact seal not found: {seal_path}"
        )

    seal_tokens = (
        seal_path.read_text(
            encoding="ascii"
        ).split()
    )

    if not seal_tokens:
        raise ValueError(
            f"Artifact seal is empty: {seal_path}"
        )

    expected_sha256 = (
        seal_tokens[0]
    )

    actual_sha256 = (
        sha256_file(
            json_path
        )
    )

    if (
        actual_sha256
        != expected_sha256
    ):
        raise ValueError(
            f"Artifact checksum mismatch: {json_path.name}"
        )

    raw: object = json.loads(
        json_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            f"{json_path.name} must contain a JSON object"
        )

    return (
        cast(
            dict[str, object],
            raw,
        ),
        actual_sha256,
    )


def _parse_source_freeze(
    cohort_dir: Path,
) -> _SourceFreeze:
    root = cohort_dir.resolve()

    manifest, manifest_sha256 = (
        _read_sealed_json(
            json_path=(
                root
                / "cohort_manifest.json"
            ),
            seal_path=(
                root
                / "cohort_manifest.sha256"
            ),
        )
    )

    schema_version = _require_int(
        manifest,
        "schema_version",
    )

    if (
        schema_version
        != COHORT_FREEZE_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported cohort freeze schema version"
        )

    if (
        _require_string(
            manifest,
            "kind",
        )
        != "v2_cohort_freeze"
    ):
        raise ValueError(
            "Artifact is not a V2 cohort freeze"
        )

    if not _require_bool(
        manifest,
        "frozen",
    ):
        raise ValueError(
            "Cohort artifact is not frozen"
        )

    dataset = _require_mapping(
        manifest,
        "dataset",
    )

    repository = _require_mapping(
        manifest,
        "repository",
    )

    experiment = _require_mapping(
        manifest,
        "experiment",
    )

    raw_patients = _require_list(
        manifest,
        "frozen_patients",
    )

    frozen_patients: list[
        _FrozenPatientReference
    ] = []

    seen_patient_ids: set[int] = set()

    for raw_patient in raw_patients:
        if not isinstance(
            raw_patient,
            dict,
        ):
            raise ValueError(
                "Frozen patient entry must be a mapping"
            )

        patient = cast(
            dict[str, object],
            raw_patient,
        )

        patient_id = _require_int(
            patient,
            "patient_id",
        )

        artifact_dir = (
            _require_string(
                patient,
                "artifact_dir",
            )
        )

        if patient_id in seen_patient_ids:
            raise ValueError(
                "Cohort freeze contains "
                f"duplicate patient {patient_id}"
            )

        seen_patient_ids.add(
            patient_id
        )

        frozen_patients.append(
            _FrozenPatientReference(
                patient_id=patient_id,
                artifact_dir=artifact_dir,
            )
        )

    return _SourceFreeze(
        manifest_sha256=(
            manifest_sha256
        ),
        dataset_name=_require_string(
            dataset,
            "name",
        ),
        dataset_version=_require_int(
            dataset,
            "version",
        ),
        dataset_doi=_require_string(
            dataset,
            "doi",
        ),
        repository_commit_sha=(
            _require_string(
                repository,
                "commit_sha",
            )
        ),
        repository_dirty=_require_bool(
            repository,
            "dirty",
        ),
        experiment_config_file=(
            _require_string(
                experiment,
                "experiment_config_file",
            )
        ),
        target_spacing=(
            _require_spacing(
                experiment,
                "target_spacing",
            )
        ),
        frozen_patients=tuple(
            frozen_patients
        ),
    )


def _resolve_artifact_dir(
    *,
    cohort_root: Path,
    relative_path: str,
) -> Path:
    path = Path(
        relative_path
    )

    if path.is_absolute():
        raise ValueError(
            "Frozen patient artifact path "
            "must be relative"
        )

    if ".." in path.parts:
        raise ValueError(
            "Frozen patient artifact path "
            "must not escape cohort directory"
        )

    resolved = (
        cohort_root
        / path
    ).resolve()

    if not resolved.is_relative_to(
        cohort_root
    ):
        raise ValueError(
            "Frozen patient artifact path "
            "must remain inside cohort directory"
        )

    return resolved


def _validate_all_artifacts(
    *,
    cohort_root: Path,
    source: _SourceFreeze,
) -> tuple[
    _ValidatedArtifact,
    ...,
]:
    validated: list[
        _ValidatedArtifact
    ] = []

    for patient in (
        source.frozen_patients
    ):
        artifact_dir = (
            _resolve_artifact_dir(
                cohort_root=cohort_root,
                relative_path=(
                    patient.artifact_dir
                ),
            )
        )

        artifact = (
            load_frozen_v2_prediction(
                artifact_dir
            )
        )

        manifest_patient_id = (
            artifact.manifest.get(
                "patient_id"
            )
        )

        if (
            type(
                manifest_patient_id
            )
            is not int
            or manifest_patient_id
            != patient.patient_id
        ):
            raise ValueError(
                "Frozen artifact patient ID "
                f"does not match cohort manifest: "
                f"{patient.patient_id}"
            )

        manifest_path = (
            artifact_dir
            / "manifest.json"
        )

        validated.append(
            _ValidatedArtifact(
                patient_id=(
                    patient.patient_id
                ),
                artifact_dir=(
                    artifact_dir
                ),
                relative_artifact_dir=(
                    patient.artifact_dir
                ),
                manifest_sha256=(
                    sha256_file(
                        manifest_path
                    )
                ),
            )
        )

    return tuple(
        validated
    )


def _validate_experiment(
    *,
    source: _SourceFreeze,
    experiment: CohortExperimentConfig,
    experiment_config_path: Path,
) -> None:
    if (
        experiment_config_path.name
        != source.experiment_config_file
    ):
        raise ValueError(
            "Experiment config does not match "
            "the frozen cohort"
        )

    for (
        actual,
        expected,
    ) in zip(
        experiment.evaluation.target_spacing,
        source.target_spacing,
        strict=True,
    ):
        if not math.isclose(
            actual,
            expected,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "Experiment target spacing "
                "does not match the frozen cohort"
            )

    selected_ids = set(
        experiment.patient_ids
    )

    for patient in (
        source.frozen_patients
    ):
        if (
            patient.patient_id
            not in selected_ids
        ):
            raise ValueError(
                f"Frozen patient "
                f"{patient.patient_id} "
                "is not selected by "
                "the experiment config"
            )


def _method_payload(
    *,
    dice: float,
    volume_error: float,
    hd95_mm: float | None,
    centroid_distance_mm: float | None,
) -> MethodMetricsPayload:
    return {
        "dice": dice,
        "relative_volume_error": (
            volume_error
        ),
        "hd95_mm": hd95_mm,
        "centroid_distance_mm": (
            centroid_distance_mm
        ),
    }


def _evaluation_payload(
    result: FrozenV2EvaluationResult,
) -> PatientEvaluationPayload:
    return {
        "patient_id": (
            result.patient_id
        ),
        "target_timepoint": (
            result.target_timepoint
        ),
        "target_day": (
            result.target_day
        ),
        "twin": _method_payload(
            dice=result.prediction_dice,
            volume_error=(
                result.prediction_volume_error
            ),
            hd95_mm=(
                result.prediction_hd95_mm
            ),
            centroid_distance_mm=(
                result
                .prediction_centroid_distance_mm
            ),
        ),
        "persistence": _method_payload(
            dice=(
                result.persistence_dice
            ),
            volume_error=(
                result.persistence_volume_error
            ),
            hd95_mm=(
                result.persistence_hd95_mm
            ),
            centroid_distance_mm=(
                result
                .persistence_centroid_distance_mm
            ),
        ),
        "volume_baseline": (
            _method_payload(
                dice=(
                    result
                    .volume_baseline_dice
                ),
                volume_error=(
                    result
                    .volume_baseline_volume_error
                ),
                hd95_mm=(
                    result
                    .volume_baseline_hd95_mm
                ),
                centroid_distance_mm=(
                    result
                    .volume_baseline_centroid_distance_mm
                ),
            )
        ),
    }


def evaluate_frozen_cohort(
    *,
    cohort_dir: Path,
    experiment_config_path: Path,
    output_dir: Path,
) -> CohortEvaluationResult:
    cohort_root = (
        cohort_dir.resolve()
    )

    destination = (
        output_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            "Cohort evaluation destination "
            f"already exists: {destination}"
        )

    source = _parse_source_freeze(
        cohort_root
    )

    experiment = (
        load_cohort_experiment_config(
            experiment_config_path
        )
    )

    _validate_experiment(
        source=source,
        experiment=experiment,
        experiment_config_path=(
            experiment_config_path
        ),
    )

    # Important anti-leakage boundary:
    # every frozen prediction is validated
    # before the first t2 is loaded.
    validated_artifacts = (
        _validate_all_artifacts(
            cohort_root=cohort_root,
            source=source,
        )
    )

    patient_results: list[
        PatientEvaluationPayload
    ] = []

    source_artifacts: list[
        SourceArtifactPayload
    ] = []

    for validated in (
        validated_artifacts
    ):
        source_artifacts.append(
            {
                "patient_id": (
                    validated.patient_id
                ),
                "artifact_dir": (
                    validated
                    .relative_artifact_dir
                ),
                "manifest_sha256": (
                    validated
                    .manifest_sha256
                ),
            }
        )

        observed_target = (
            prepare_patient_timepoint(
                metadata_root=(
                    experiment.metadata_root
                ),
                patients_root=(
                    experiment.patients_root
                ),
                patient_id=(
                    validated.patient_id
                ),
                timepoint_name="t2",
                target_spacing=(
                    source.target_spacing
                ),
            )
        )

        evaluation = (
            evaluate_frozen_v2_prediction(
                artifact_dir=(
                    validated.artifact_dir
                ),
                observed_target=(
                    observed_target
                ),
            )
        )

        patient_results.append(
            _evaluation_payload(
                evaluation
            )
        )

    manifest: (
        CohortEvaluationPayload
    ) = {
        "schema_version": (
            COHORT_EVALUATION_SCHEMA_VERSION
        ),
        "kind": (
            "v2_cohort_evaluation"
        ),
        "sealed": True,
        "source_freeze_manifest_sha256": (
            source.manifest_sha256
        ),
        "dataset": {
            "name": source.dataset_name,
            "version": (
                source.dataset_version
            ),
            "doi": source.dataset_doi,
        },
        "repository": {
            "commit_sha": (
                source.repository_commit_sha
            ),
            "dirty": (
                source.repository_dirty
            ),
        },
        "target_spacing": list(
            source.target_spacing
        ),
        "source_artifacts": (
            source_artifacts
        ),
        "patients": (
            patient_results
        ),
    }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=(
                f".{destination.name}-"
            ),
        )
    )

    try:
        manifest_path = (
            temporary
            / "cohort_evaluation.json"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            temporary
            / "cohort_evaluation.sha256"
        ).write_text(
            (
                sha256_file(
                    manifest_path
                )
                + "  cohort_evaluation.json\n"
            ),
            encoding="ascii",
        )

        temporary.rename(
            destination
        )

    except BaseException:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    return CohortEvaluationResult(
        directory=destination,
        manifest=manifest,
    )