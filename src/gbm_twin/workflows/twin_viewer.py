from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationPayload,
    PatientEvaluationPayload,
    SourceArtifactPayload,
)
from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.prediction import (
    load_frozen_v2_prediction,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)
from gbm_twin.workflows.viewer import (
    ViewerPlane,
    ViewerVolumeMetadata,
    get_viewer_volume_metadata,
    render_viewer_mask_slice_png,
    render_viewer_slice_png,
)

TwinOverlayLayer = Literal[
    "twin",
    "persistence",
    "volume_baseline",
    "observed",
]


def _find_patient(
    payload: CohortEvaluationPayload,
    patient_id: int,
) -> PatientEvaluationPayload:
    for patient in payload["patients"]:
        if (
            patient["patient_id"]
            == patient_id
        ):
            return patient

    raise KeyError(
        f"Patient {patient_id} is not "
        "present in the sealed "
        "V2 evaluation"
    )


def _find_source_artifact(
    payload: CohortEvaluationPayload,
    patient_id: int,
) -> SourceArtifactPayload:
    for artifact in (
        payload["source_artifacts"]
    ):
        if (
            artifact["patient_id"]
            == patient_id
        ):
            return artifact

    raise KeyError(
        "Frozen source artifact is "
        f"missing for patient {patient_id}"
    )


def _target_spacing(
    payload: CohortEvaluationPayload,
) -> tuple[
    float,
    float,
    float,
]:
    spacing = (
        payload["target_spacing"]
    )

    if len(spacing) != 3:
        raise ValueError(
            "Twin target spacing must "
            "contain three values"
        )

    return (
        float(spacing[0]),
        float(spacing[1]),
        float(spacing[2]),
    )


def _resolve_artifact_dir(
    *,
    cohort_freeze_root: Path,
    relative_path: str,
) -> Path:
    root = (
        cohort_freeze_root
        .resolve()
    )

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
            "must remain inside "
            "cohort root"
        )

    return resolved


def _load_patient_artifact(
    *,
    cohort_freeze_root: Path,
    payload: CohortEvaluationPayload,
    patient_id: int,
):
    reference = (
        _find_source_artifact(
            payload,
            patient_id,
        )
    )

    artifact_dir = (
        _resolve_artifact_dir(
            cohort_freeze_root=(
                cohort_freeze_root
            ),
            relative_path=(
                reference[
                    "artifact_dir"
                ]
            ),
        )
    )

    manifest_path = (
        artifact_dir
        / "manifest.json"
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

    return (
        load_frozen_v2_prediction(
            artifact_dir
        )
    )


def get_twin_viewer_volume_metadata(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_evaluation_root: Path,
    patient_id: int,
) -> ViewerVolumeMetadata:
    evaluation = (
        load_sealed_cohort_evaluation(
            cohort_evaluation_root
        )
    )

    patient = _find_patient(
        evaluation.manifest,
        patient_id,
    )

    spacing = _target_spacing(
        evaluation.manifest
    )

    return (
        get_viewer_volume_metadata(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=(
                patient[
                    "target_timepoint"
                ]
            ),
            target_spacing=spacing,
        )
    )


def render_twin_viewer_slice_png(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    patient_id: int,
    layer: TwinOverlayLayer,
    plane: ViewerPlane,
    index: int | None = None,
) -> bytes:
    evaluation = (
        load_sealed_cohort_evaluation(
            cohort_evaluation_root
        )
    )

    payload = evaluation.manifest

    patient = _find_patient(
        payload,
        patient_id,
    )

    spacing = _target_spacing(
        payload
    )

    target_timepoint = (
        patient["target_timepoint"]
    )

    if layer == "observed":
        return render_viewer_slice_png(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=(
                target_timepoint
            ),
            plane=plane,
            index=index,
            overlay_gtv=True,
            target_spacing=spacing,
        )

    artifact = (
        _load_patient_artifact(
            cohort_freeze_root=(
                cohort_freeze_root
            ),
            payload=payload,
            patient_id=patient_id,
        )
    )

    if layer == "twin":
        mask = np.asarray(
            artifact.prediction_mask
        )

        color = (
            37.0,
            99.0,
            235.0,
        )

    elif layer == "persistence":
        mask = np.asarray(
            artifact.persistence_mask
        )

        color = (
            217.0,
            119.0,
            6.0,
        )

    elif (
        layer
        == "volume_baseline"
    ):
        mask = np.asarray(
            artifact
            .volume_baseline_mask
        )

        color = (
            124.0,
            58.0,
            237.0,
        )

    else:
        raise ValueError(
            f"Unsupported twin layer: {layer}"
        )

    return (
        render_viewer_mask_slice_png(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=(
                target_timepoint
            ),
            overlay_mask=mask,
            plane=plane,
            index=index,
            overlay_color=color,
            overlay_alpha=0.52,
            target_spacing=spacing,
        )
    )