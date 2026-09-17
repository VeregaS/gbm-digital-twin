from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.patients import (
    prepare_patient_timepoint,
)
from gbm_twin.workflows.scene3d import (
    SurfaceMesh,
    surface_mesh_from_mask,
)
from gbm_twin.workflows.twin_artifacts import (
    find_evaluated_patient,
    load_frozen_patient_artifact,
    target_spacing,
)

BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class TwinViewer3DScene:
    patient_id: int
    timepoint_name: str

    spacing: tuple[
        float,
        float,
        float,
    ]

    brain: SurfaceMesh
    observed: SurfaceMesh

    twin: SurfaceMesh
    persistence: SurfaceMesh

    volume_baseline: SurfaceMesh


def _as_bool_mask(
    data: object,
) -> BoolArray:
    return np.asarray(
        data,
        dtype=np.bool_,
    )


def _validate_shape(
    *,
    name: str,
    mask: BoolArray,
    expected_shape: tuple[int, ...],
) -> None:
    if mask.shape != expected_shape:
        raise ValueError(
            f"{name} shape {mask.shape} "
            "does not match observed "
            f"target shape {expected_shape}"
        )


def get_twin_viewer_3d_scene(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    patient_id: int,
) -> TwinViewer3DScene:
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
        patient[
            "target_timepoint"
        ]
    )

    observed_target = (
        prepare_patient_timepoint(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=(
                target_timepoint
            ),
            target_spacing=spacing,
        )
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

    brain_mask = _as_bool_mask(
        observed_target
        .brain_mask
        .data
        > 0.5
    )

    observed_mask = _as_bool_mask(
        observed_target
        .gtv
        .data
        > 0.5
    )

    twin_mask = _as_bool_mask(
        artifact.prediction_mask
    )

    persistence_mask = _as_bool_mask(
        artifact.persistence_mask
    )

    volume_baseline_mask = (
        _as_bool_mask(
            artifact
            .volume_baseline_mask
        )
    )

    expected_shape = (
        observed_mask.shape
    )

    _validate_shape(
        name="brain",
        mask=brain_mask,
        expected_shape=expected_shape,
    )

    _validate_shape(
        name="twin",
        mask=twin_mask,
        expected_shape=expected_shape,
    )

    _validate_shape(
        name="persistence",
        mask=persistence_mask,
        expected_shape=expected_shape,
    )

    _validate_shape(
        name="volume baseline",
        mask=volume_baseline_mask,
        expected_shape=expected_shape,
    )

    brain = surface_mesh_from_mask(
        brain_mask,
        spacing=spacing,
        name="brain",
        step_size=1,
        smoothing_sigma_voxels=1.15,
    )

    observed = (
        surface_mesh_from_mask(
            observed_mask,
            spacing=spacing,
            name="observed",
            step_size=1,
            smoothing_sigma_voxels=0.25,
        )
    )

    twin = surface_mesh_from_mask(
        twin_mask,
        spacing=spacing,
        name="twin",
        step_size=1,
        smoothing_sigma_voxels=0.25,
    )

    persistence = (
        surface_mesh_from_mask(
            persistence_mask,
            spacing=spacing,
            name="persistence",
            step_size=1,
            smoothing_sigma_voxels=0.25,
        )
    )

    volume_baseline = (
        surface_mesh_from_mask(
            volume_baseline_mask,
            spacing=spacing,
            name="volume_baseline",
            step_size=1,
            smoothing_sigma_voxels=0.25,
        )
    )

    return TwinViewer3DScene(
        patient_id=patient_id,
        timepoint_name=(
            target_timepoint
        ),
        spacing=spacing,
        brain=brain,
        observed=observed,
        twin=twin,
        persistence=persistence,
        volume_baseline=(
            volume_baseline
        ),
    )