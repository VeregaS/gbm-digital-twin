from __future__ import annotations

from pathlib import Path
from typing import Literal

import numpy as np

from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.twin_artifacts import (
    find_evaluated_patient,
    load_frozen_patient_artifact,
    target_spacing,
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

    patient = find_evaluated_patient(
        evaluation.manifest,
        patient_id,
    )

    spacing = target_spacing(
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

    patient = find_evaluated_patient(
        payload,
        patient_id,
    )

    spacing = target_spacing(
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
        load_frozen_patient_artifact(
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

    elif layer == "volume_baseline":
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
            "Unsupported twin layer: "
            f"{layer}"
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