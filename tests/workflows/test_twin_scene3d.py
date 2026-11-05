from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.twin_scene3d as scene_module
from gbm_twin.data.nifti import (
    NiftiVolume,
)
from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationPayload,
    CohortEvaluationResult,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)
from gbm_twin.workflows.twin_scene3d import (
    get_twin_viewer_3d_scene,
)


def make_payload(
) -> CohortEvaluationPayload:
    return {
        "schema_version": 1,
        "kind": (
            "v2_cohort_evaluation"
        ),
        "sealed": True,
        "source_freeze_manifest_sha256": (
            "a" * 64
        ),
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": (
                "10.7937/v9pn-2f72"
            ),
        },
        "repository": {
            "commit_sha": (
                "0123456789abcdef"
                "0123456789abcdef"
                "01234567"
            ),
            "dirty": False,
        },
        "target_spacing": [
            2.0,
            2.0,
            2.0,
        ],
        "source_artifacts": [
            {
                "patient_id": 42,
                "artifact_dir": (
                    "patients/"
                    "patient-42/"
                    "frozen-v2"
                ),
                "manifest_sha256": (
                    "b" * 64
                ),
            },
        ],
        "patients": [
            {
                "patient_id": 42,
                "target_timepoint": "t2",
                "target_day": 120.0,
                "twin": {
                    "dice": 0.8,
                    "relative_volume_error": 0.1,
                    "hd95_mm": 4.0,
                    "centroid_distance_mm": 2.0,
                },
                "persistence": {
                    "dice": 0.6,
                    "relative_volume_error": 0.2,
                    "hd95_mm": 8.0,
                    "centroid_distance_mm": 4.0,
                },
                "volume_baseline": {
                    "dice": 0.5,
                    "relative_volume_error": 0.05,
                    "hd95_mm": 10.0,
                    "centroid_distance_mm": 5.0,
                },
            },
        ],
    }


def make_volume(
    name: str,
    data: np.ndarray,
) -> NiftiVolume:
    return NiftiVolume(
        path=Path(name),
        data=data,
        affine=np.eye(
            4,
            dtype=np.float64,
        ),
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )


def make_target(
) -> PreparedPatientTimepoint:
    observed = np.zeros(
        (10, 10, 10),
        dtype=np.float32,
    )

    observed[
        3:7,
        3:7,
        3:7,
    ] = 1.0

    brain = np.ones(
        (10, 10, 10),
        dtype=np.float32,
    )

    return PreparedPatientTimepoint(
        patient_id=42,
        name="t2",
        days_from_baseline=120.0,
        t1gd=make_volume(
            "t2_t1gd.nii.gz",
            observed.copy(),
        ),
        gtv=make_volume(
            "t2_gtv.nii.gz",
            observed,
        ),
        brain_mask=make_volume(
            "t2_brain.nii.gz",
            brain,
        ),
    )


def make_artifact(
    tmp_path: Path,
) -> FrozenV2PredictionArtifact:
    prediction = np.zeros(
        (10, 10, 10),
        dtype=bool,
    )

    prediction[
        4:8,
        3:7,
        3:7,
    ] = True

    persistence = np.zeros(
        (10, 10, 10),
        dtype=bool,
    )

    persistence[
        3:7,
        3:7,
        3:7,
    ] = True

    volume = np.zeros(
        (10, 10, 10),
        dtype=bool,
    )

    volume[
        2:8,
        2:8,
        2:8,
    ] = True

    return FrozenV2PredictionArtifact(
        directory=tmp_path,
        manifest={
            "patient_id": 42,
        },
        prediction_field=(
            prediction.astype(
                np.float32
            )
        ),
        prediction_mask=prediction,
        persistence_mask=(
            persistence
        ),
        volume_baseline_mask=(
            volume
        ),
    )


def test_builds_twin_3d_scene(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = make_payload()

    evaluation = (
        CohortEvaluationResult(
            directory=(
                tmp_path
                / "evaluation"
            ),
            manifest=payload,
        )
    )

    target = make_target()

    artifact = make_artifact(
        tmp_path
        / "artifact"
    )

    def fake_load_evaluation(
        directory: Path,
    ) -> CohortEvaluationResult:
        return evaluation

    def fake_prepare(
        *,
        metadata_root: Path,
        patients_root: Path,
        patient_id: int,
        timepoint_name: str,
        target_spacing: tuple[
            float,
            float,
            float,
        ],
    ) -> PreparedPatientTimepoint:
        assert patient_id == 42
        assert timepoint_name == "t2"

        assert target_spacing == (
            2.0,
            2.0,
            2.0,
        )

        return target

    def fake_load_artifact(
        *,
        cohort_freeze_root: Path,
        payload: CohortEvaluationPayload,
        patient_id: int,
    ) -> FrozenV2PredictionArtifact:
        assert patient_id == 42

        return artifact

    monkeypatch.setattr(
        scene_module,
        "load_sealed_cohort_evaluation",
        fake_load_evaluation,
    )

    monkeypatch.setattr(
        scene_module,
        "prepare_patient_timepoint",
        fake_prepare,
    )

    monkeypatch.setattr(
        scene_module,
        "load_frozen_patient_artifact",
        fake_load_artifact,
    )

    scene = get_twin_viewer_3d_scene(
        metadata_root=(
            tmp_path
            / "metadata"
        ),
        patients_root=(
            tmp_path
            / "patients"
        ),
        cohort_freeze_root=(
            tmp_path
            / "freeze"
        ),
        cohort_evaluation_root=(
            tmp_path
            / "evaluation"
        ),
        patient_id=42,
    )

    assert scene.patient_id == 42

    assert (
        scene.timepoint_name
        == "t2"
    )

    assert scene.spacing == (
        2.0,
        2.0,
        2.0,
    )

    assert (
        scene.brain
        .triangle_count
        > 0
    )

    assert (
        scene.observed
        .triangle_count
        > 0
    )

    assert (
        scene.twin
        .triangle_count
        > 0
    )

    assert (
        scene.persistence
        .triangle_count
        > 0
    )

    assert (
        scene.volume_baseline
        .triangle_count
        > 0
    )