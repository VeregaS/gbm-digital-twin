from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.twin_qc as qc_module
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
from gbm_twin.workflows.twin_qc import (
    TwinQCWarningCode,
    get_twin_patient_qc,
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
                "patient_id": 251,
                "artifact_dir": (
                    "patients/"
                    "patient-251/"
                    "frozen-v2"
                ),
                "manifest_sha256": (
                    "b" * 64
                ),
            },
        ],
        "patients": [
            {
                "patient_id": 251,
                "target_timepoint": "t2",
                "target_day": 100.0,
                "twin": {
                    "dice": 0.5,
                    "relative_volume_error": 0.2,
                    "hd95_mm": 8.0,
                    "centroid_distance_mm": 4.0,
                },
                "persistence": {
                    "dice": 0.4,
                    "relative_volume_error": 0.3,
                    "hd95_mm": 10.0,
                    "centroid_distance_mm": 5.0,
                },
                "volume_baseline": {
                    "dice": 0.3,
                    "relative_volume_error": 0.4,
                    "hd95_mm": 12.0,
                    "centroid_distance_mm": 6.0,
                },
            },
        ],
    }


def make_volume(
    path: str,
    data: np.ndarray,
) -> NiftiVolume:
    return NiftiVolume(
        path=Path(path),
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


def test_qc_detects_outside_brain_and_fragmentation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = make_payload()

    evaluation = CohortEvaluationResult(
        directory=(
            tmp_path
            / "evaluation"
        ),
        manifest=payload,
    )

    brain = np.zeros(
        (12, 12, 12),
        dtype=np.float32,
    )

    brain[
        2:10,
        2:10,
        2:10,
    ] = 1.0

    observed = np.zeros(
        (12, 12, 12),
        dtype=np.float32,
    )

    observed[
        1:5,
        3:7,
        3:7,
    ] = 1.0

    target = PreparedPatientTimepoint(
        patient_id=251,
        name="t2",
        days_from_baseline=100.0,
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

    twin = np.zeros(
        (12, 12, 12),
        dtype=bool,
    )

    twin[
        3:6,
        3:6,
        3:6,
    ] = True

    twin[
        8:10,
        8:10,
        8:10,
    ] = True

    artifact = FrozenV2PredictionArtifact(
        directory=(
            tmp_path
            / "artifact"
        ),
        manifest={
            "patient_id": 251,
        },
        prediction_field=(
            twin.astype(
                np.float32
            )
        ),
        prediction_mask=twin,
        persistence_mask=(
            twin.copy()
        ),
        volume_baseline_mask=(
            twin.copy()
        ),
    )

    def fake_evaluation(
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
        return target

    def fake_artifact(
        *,
        cohort_freeze_root: Path,
        payload: CohortEvaluationPayload,
        patient_id: int,
    ) -> FrozenV2PredictionArtifact:
        return artifact

    monkeypatch.setattr(
        qc_module,
        "load_sealed_cohort_evaluation",
        fake_evaluation,
    )

    monkeypatch.setattr(
        qc_module,
        "prepare_patient_timepoint",
        fake_prepare,
    )

    monkeypatch.setattr(
        qc_module,
        "load_frozen_patient_artifact",
        fake_artifact,
    )

    result = get_twin_patient_qc(
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
        patient_id=251,
    )

    codes = {
        warning.code
        for warning
        in result.warnings
    }

    assert (
        TwinQCWarningCode
        .OBSERVED_OUTSIDE_BRAIN
        in codes
    )

    assert (
        TwinQCWarningCode
        .TWIN_FRAGMENTED
        in codes
    )

    assert (
        result.observed
        .outside_brain_fraction
        is not None
    )

    assert (
        result.observed
        .outside_brain_fraction
        > 0.0
    )