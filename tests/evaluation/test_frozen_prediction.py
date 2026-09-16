from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import gbm_twin.evaluation.frozen_prediction as evaluation_module
from gbm_twin.data.nifti import (
    NiftiVolume,
)
from gbm_twin.evaluation.frozen_prediction import (
    evaluate_frozen_v2_prediction,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)


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


def make_observed_target(
) -> PreparedPatientTimepoint:
    observed = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    observed[
        2,
        2,
        2,
    ] = 1.0

    volume = make_volume(
        "t2_gtv.nii.gz",
        observed,
    )

    return PreparedPatientTimepoint(
        patient_id=42,
        name="t2",
        days_from_baseline=120.0,
        t1gd=make_volume(
            "t2_t1gd.nii.gz",
            observed.copy(),
        ),
        gtv=volume,
        brain_mask=make_volume(
            "t2_brain_mask.nii.gz",
            np.ones(
                (5, 5, 5),
                dtype=np.uint8,
            ),
        ),
    )


def make_artifact(
    directory: Path,
) -> FrozenV2PredictionArtifact:
    prediction = np.zeros(
        (5, 5, 5),
        dtype=bool,
    )

    prediction[
        3,
        2,
        2,
    ] = True

    persistence = np.zeros_like(
        prediction
    )

    persistence[
        2,
        2,
        2,
    ] = True

    volume_baseline = np.zeros_like(
        prediction
    )

    prediction_field = (
        prediction.astype(
            np.float32
        )
    )

    return FrozenV2PredictionArtifact(
        directory=directory,
        manifest={
            "patient_id": 42,
            "prediction_horizon": {
                "target_timepoint": "t2",
                "target_day": 120.0,
            },
            "geometry": {
                "shape": [
                    5,
                    5,
                    5,
                ],
                "spacing": [
                    2.0,
                    2.0,
                    2.0,
                ],
                "affine": (
                    np.eye(
                        4,
                        dtype=np.float64,
                    ).tolist()
                ),
            },
            "parameters": {
                "observation_threshold": 0.5,
            },
        },
        prediction_field=(
            prediction_field
        ),
        prediction_mask=prediction,
        persistence_mask=persistence,
        volume_baseline_mask=(
            volume_baseline
        ),
    )


def test_evaluate_frozen_prediction_includes_spatial_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact = make_artifact(
        tmp_path
    )

    def fake_load(
        artifact_dir: Path,
    ) -> FrozenV2PredictionArtifact:
        assert artifact_dir == tmp_path

        return artifact

    monkeypatch.setattr(
        evaluation_module,
        "load_frozen_v2_prediction",
        fake_load,
    )

    result = (
        evaluate_frozen_v2_prediction(
            artifact_dir=tmp_path,
            observed_target=(
                make_observed_target()
            ),
        )
    )

    assert result.patient_id == 42
    assert result.target_timepoint == "t2"
    assert result.target_day == 120.0

    assert result.prediction_dice == 0.0
    assert result.prediction_volume_error == 0.0

    assert (
        result.prediction_hd95_mm
        is not None
    )

    assert np.isclose(
        result.prediction_hd95_mm,
        2.0,
    )

    assert (
        result
        .prediction_centroid_distance_mm
        is not None
    )

    assert np.isclose(
        result
        .prediction_centroid_distance_mm,
        2.0,
    )

    assert (
        result.persistence_dice
        == 1.0
    )

    assert (
        result.persistence_volume_error
        == 0.0
    )

    assert (
        result.persistence_hd95_mm
        == 0.0
    )

    assert (
        result
        .persistence_centroid_distance_mm
        == 0.0
    )

    assert (
        result.volume_baseline_dice
        == 0.0
    )

    assert (
        result.volume_baseline_volume_error
        == 1.0
    )

    assert (
        result.volume_baseline_hd95_mm
        is None
    )

    assert (
        result
        .volume_baseline_centroid_distance_mm
        is None
    )


def test_evaluate_rejects_target_day_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact = make_artifact(
        tmp_path
    )

    monkeypatch.setattr(
        evaluation_module,
        "load_frozen_v2_prediction",
        lambda artifact_dir: artifact,
    )

    target = (
        make_observed_target()
    )

    mismatched = (
        PreparedPatientTimepoint(
            patient_id=target.patient_id,
            name=target.name,
            days_from_baseline=121.0,
            t1gd=target.t1gd,
            gtv=target.gtv,
            brain_mask=(
                target.brain_mask
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="target day",
    ):
        evaluate_frozen_v2_prediction(
            artifact_dir=tmp_path,
            observed_target=mismatched,
        )