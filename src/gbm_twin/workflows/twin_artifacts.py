from __future__ import annotations

from pathlib import Path
from typing import cast

from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationPayload,
    PatientEvaluationPayload,
    SourceArtifactPayload,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
    load_frozen_v2_prediction,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)


def find_evaluated_patient(
    payload: CohortEvaluationPayload,
    patient_id: int,
) -> PatientEvaluationPayload:
    for patient in payload["patients"]:
        if patient["patient_id"] == patient_id:
            return patient

    raise KeyError(
        f"Patient {patient_id} is not "
        "present in the sealed V2 evaluation"
    )


def find_source_artifact(
    payload: CohortEvaluationPayload,
    patient_id: int,
) -> SourceArtifactPayload:
    for artifact in payload["source_artifacts"]:
        if artifact["patient_id"] == patient_id:
            return artifact

    raise KeyError(
        "Frozen source artifact is "
        f"missing for patient {patient_id}"
    )


def target_spacing(
    payload: CohortEvaluationPayload,
) -> tuple[
    float,
    float,
    float,
]:
    spacing = payload["target_spacing"]

    if len(spacing) != 3:
        raise ValueError(
            "Twin target spacing must "
            "contain three values"
        )

    result = (
        float(spacing[0]),
        float(spacing[1]),
        float(spacing[2]),
    )

    if any(
        value <= 0.0
        for value in result
    ):
        raise ValueError(
            "Twin target spacing must "
            "contain positive values"
        )

    return result


def validate_source_freeze(
    *,
    cohort_freeze_root: Path,
    payload: CohortEvaluationPayload,
) -> None:
    root = cohort_freeze_root.resolve()

    manifest_path = (
        root
        / "cohort_manifest.json"
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Source cohort freeze manifest "
            f"not found: {manifest_path}"
        )

    actual_sha256 = sha256_file(
        manifest_path
    )

    expected_sha256 = (
        payload[
            "source_freeze_manifest_sha256"
        ]
    )

    if actual_sha256 != expected_sha256:
        raise ValueError(
            "Source cohort freeze does not "
            "match sealed evaluation"
        )


def _resolve_artifact_dir(
    *,
    cohort_freeze_root: Path,
    relative_path: str,
) -> Path:
    root = cohort_freeze_root.resolve()

    relative = Path(
        relative_path
    )

    if relative.is_absolute():
        raise ValueError(
            "Frozen artifact path "
            "must be relative"
        )

    if ".." in relative.parts:
        raise ValueError(
            "Frozen artifact path "
            "must not escape cohort root"
        )

    resolved = (
        root
        / relative
    ).resolve()

    if not resolved.is_relative_to(
        root
    ):
        raise ValueError(
            "Frozen artifact path "
            "must remain inside cohort root"
        )

    return resolved


def load_frozen_patient_artifact(
    *,
    cohort_freeze_root: Path,
    payload: CohortEvaluationPayload,
    patient_id: int,
) -> FrozenV2PredictionArtifact:
    validate_source_freeze(
        cohort_freeze_root=(
            cohort_freeze_root
        ),
        payload=payload,
    )

    reference = find_source_artifact(
        payload,
        patient_id,
    )

    artifact_dir = (
        _resolve_artifact_dir(
            cohort_freeze_root=(
                cohort_freeze_root
            ),
            relative_path=(
                reference["artifact_dir"]
            ),
        )
    )

    manifest_path = (
        artifact_dir
        / "manifest.json"
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Frozen prediction manifest "
            f"not found: {manifest_path}"
        )

    actual_sha256 = sha256_file(
        manifest_path
    )

    if (
        actual_sha256
        != reference[
            "manifest_sha256"
        ]
    ):
        raise ValueError(
            "Frozen prediction manifest "
            "does not match sealed "
            "cohort evaluation"
        )

    artifact = (
        load_frozen_v2_prediction(
            artifact_dir
        )
    )

    manifest = cast(
        dict[str, object],
        artifact.manifest,
    )

    raw_patient_id = (
        manifest.get(
            "patient_id"
        )
    )

    if type(raw_patient_id) is not int:
        raise ValueError(
            "Frozen prediction patient_id "
            "must be an integer"
        )

    artifact_patient_id = cast(
        int,
        raw_patient_id,
    )

    if artifact_patient_id != patient_id:
        raise ValueError(
            "Frozen prediction patient "
            "does not match requested patient"
        )

    return artifact