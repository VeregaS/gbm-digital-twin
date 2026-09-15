import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.prediction as prediction_module
from gbm_twin.calibration.grid_search import CalibrationResult
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.evaluation.frozen_prediction import (
    evaluate_frozen_v2_prediction,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.treatment import PIRTFractionatedRadiotherapy
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    V2CalibrationRun,
)
from gbm_twin.workflows.contracts import PredictionTarget
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.prediction import (
    V2_ASSIMILATION_RULE,
    FrozenV2PredictionArtifact,
    freeze_v2_prediction,
    load_frozen_v2_prediction,
)


@dataclass
class CapturedCalls:
    calibration_calls: int = 0
    calibration_start: PreparedPatientTimepoint | None = None
    calibration_observed: PreparedPatientTimepoint | None = None
    calibration_treatment: PIRTFractionatedRadiotherapy | None = None
    simulation_treatment: PIRTFractionatedRadiotherapy | None = None
    simulation_start_time_day: float | None = None
    simulation_duration_days: float | None = None


def make_volume(
    name: str,
    active: tuple[tuple[int, int, int], ...],
) -> NiftiVolume:
    data = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    for index in active:
        data[index] = 1.0

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


def make_brain_volume(
    name: str,
) -> NiftiVolume:
    return NiftiVolume(
        path=Path(name),
        data=np.ones(
            (5, 5, 5),
            dtype=np.float32,
        ),
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


def make_timepoint(
    *,
    name: str,
    day: float,
    active: tuple[tuple[int, int, int], ...],
) -> PreparedPatientTimepoint:
    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=make_volume(
            f"{name}_t1gd.nii.gz",
            active,
        ),
        gtv=make_volume(
            f"{name}_gtv.nii.gz",
            active,
        ),
        brain_mask=make_brain_volume(
            f"{name}_brain.nii.gz",
        ),
    )


def make_target() -> PredictionTarget:
    return PredictionTarget(
        timepoint_name="t2",
        target_day=120.0,
    )


def make_config() -> V2CalibrationConfig:
    return V2CalibrationConfig(
        diffusion_values=(
            0.01,
            0.03,
            0.05,
        ),
        proliferation_values=(
            0.005,
            0.015,
            0.025,
        ),
    )


def make_calibration_run() -> V2CalibrationRun:
    best = CalibrationResult(
        diffusion=0.03,
        proliferation=0.015,
        dice=0.8,
        volume_error=0.1,
        loss=0.25,
    )

    return V2CalibrationRun(
        patient_id=42,
        start_timepoint="t0",
        observed_timepoint="t1",
        start_day=0.0,
        observed_day=60.0,
        duration_days=60.0,
        best=best,
        coarse_best=best,
        candidates=(best,),
        coarse_candidates=(best,),
        refined_candidates=(best,),
        refined_diffusion_values=(
            0.02,
            0.03,
            0.04,
        ),
        refined_proliferation_values=(
            0.01,
            0.015,
            0.02,
        ),
    )


def build_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    treatment: PIRTFractionatedRadiotherapy | None = None,
) -> tuple[
    FrozenV2PredictionArtifact,
    CapturedCalls,
    PreparedPatientTimepoint,
    PreparedPatientTimepoint,
    PredictionTarget,
]:
    t0 = make_timepoint(
        name="t0",
        day=0.0,
        active=(
            (2, 2, 2),
        ),
    )

    t1 = make_timepoint(
        name="t1",
        day=60.0,
        active=(
            (2, 2, 2),
            (2, 2, 3),
        ),
    )

    predicted_field = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    predicted_field[2, 2, 2] = 0.9
    predicted_field[2, 2, 3] = 0.8
    predicted_field[2, 3, 3] = 0.7

    captured = CapturedCalls()

    def fake_calibration(
        *,
        start: PreparedPatientTimepoint,
        observed: PreparedPatientTimepoint,
        treatment: PIRTFractionatedRadiotherapy | None,
        config: V2CalibrationConfig,
        cache_dir: Path,
        workers: int = 1,
    ) -> V2CalibrationRun:
        captured.calibration_calls += 1
        captured.calibration_start = start
        captured.calibration_observed = observed
        captured.calibration_treatment = treatment

        return make_calibration_run()

    def fake_simulation(
        initial_field: np.ndarray,
        params: ReactionDiffusionParameters,
        *,
        spacing: tuple[float, float, float],
        duration_days: float,
        dt: float,
        domain_mask: np.ndarray | None = None,
        treatment: PIRTFractionatedRadiotherapy | None = None,
        start_time_day: float = 0.0,
        crop_to_domain: bool = True,
    ) -> np.ndarray:
        captured.simulation_treatment = treatment
        captured.simulation_start_time_day = start_time_day
        captured.simulation_duration_days = duration_days

        return predicted_field.copy()

    monkeypatch.setattr(
        prediction_module,
        "calibrate_v2_interval",
        fake_calibration,
    )

    monkeypatch.setattr(
        prediction_module,
        "simulate_reaction_diffusion",
        fake_simulation,
    )

    output_dir = (
        tmp_path
        / "patient-42-t1-to-t2"
    )

    target = make_target()

    artifact = freeze_v2_prediction(
        start=t0,
        observed=t1,
        target=target,
        treatment=treatment,
        config=make_config(),
        cache_dir=tmp_path / "cache",
        output_dir=output_dir,
        workers=2,
    )

    return (
        artifact,
        captured,
        t0,
        t1,
        target,
    )


def test_freeze_v2_prediction_seals_protocol_before_t2_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    (
        artifact,
        captured,
        t0,
        t1,
        target,
    ) = build_artifact(
        monkeypatch,
        tmp_path,
    )

    manifest = artifact.manifest

    assert manifest["sealed"] is True
    assert manifest["model_version"] == "V2"

    assert manifest["calibration_interval"] == {
        "start_timepoint": "t0",
        "start_day": 0.0,
        "observed_timepoint": "t1",
        "observed_day": 60.0,
        "duration_days": 60.0,
    }

    assert manifest["prediction_horizon"] == {
        "start_timepoint": "t1",
        "start_day": 60.0,
        "target_timepoint": "t2",
        "target_day": 120.0,
        "duration_days": 60.0,
    }

    assert (
        manifest["parameters"]["diffusion"]
        == 0.03
    )

    assert (
        manifest["parameters"]["proliferation"]
        == 0.015
    )

    assert (
        manifest["parameters"]["assimilation_rule"]
        == V2_ASSIMILATION_RULE
    )

    assert captured.calibration_start is t0
    assert captured.calibration_observed is t1

    assert (
        captured.simulation_start_time_day
        == 60.0
    )

    assert (
        captured.simulation_duration_days
        == 60.0
    )

    assert target.timepoint_name == "t2"
    assert target.target_day == 120.0

    assert (
        np.count_nonzero(
            artifact.prediction_mask
        )
        == 3
    )

    artifact_filenames = {
        path.name
        for path in artifact.directory.iterdir()
    }

    assert artifact_filenames == {
        "manifest.json",
        "manifest.sha256",
        "prediction_field.npy",
        "prediction_mask.npy",
        "persistence_mask.npy",
        "volume_baseline_mask.npy",
    }

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        freeze_v2_prediction(
            start=t0,
            observed=t1,
            target=target,
            treatment=None,
            config=make_config(),
            cache_dir=tmp_path / "cache",
            output_dir=artifact.directory,
        )

    assert captured.calibration_calls == 1


def test_load_frozen_prediction_rejects_modified_array(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _, _ = build_artifact(
        monkeypatch,
        tmp_path,
    )

    path = (
        artifact.directory
        / "prediction_mask.npy"
    )

    modified = np.zeros(
        (5, 5, 5),
        dtype=np.uint8,
    )

    np.save(
        path,
        modified,
        allow_pickle=False,
    )

    with pytest.raises(
        ValueError,
        match="checksum mismatch",
    ):
        load_frozen_v2_prediction(
            artifact.directory
        )


def test_freeze_records_complete_pirt_protocol(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    treatment = PIRTFractionatedRadiotherapy(
        fraction_days=(
            10.0,
            11.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.01,
        beta_per_gy2=0.001,
    )

    (
        artifact,
        captured,
        _,
        _,
        _,
    ) = build_artifact(
        monkeypatch,
        tmp_path,
        treatment,
    )

    assert artifact.manifest["treatment"] == {
        "kind": "pirt_fractionated_radiotherapy",
        "fraction_days": [
            10.0,
            11.0,
        ],
        "dose_per_fraction_gy": 2.0,
        "alpha_per_gy": 0.01,
        "beta_per_gy2": 0.001,
    }

    assert (
        captured.calibration_treatment
        is treatment
    )

    assert (
        captured.simulation_treatment
        is treatment
    )


def test_load_frozen_prediction_rejects_modified_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _, _ = build_artifact(
        monkeypatch,
        tmp_path,
    )

    path = (
        artifact.directory
        / "manifest.json"
    )

    path.write_text(
        (
            path.read_text(
                encoding="utf-8",
            )
            + " "
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="manifest checksum mismatch",
    ):
        load_frozen_v2_prediction(
            artifact.directory
        )


def test_evaluator_receives_t2_only_after_artifact_is_frozen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _, _ = build_artifact(
        monkeypatch,
        tmp_path,
    )

    manifest_path = (
        artifact.directory
        / "manifest.json"
    )

    manifest_before = (
        manifest_path.read_bytes()
    )

    t2 = make_timepoint(
        name="t2",
        day=120.0,
        active=(
            (2, 2, 2),
            (2, 2, 3),
            (2, 3, 3),
        ),
    )

    result = (
        evaluate_frozen_v2_prediction(
            artifact_dir=artifact.directory,
            observed_target=t2,
        )
    )

    assert result.patient_id == 42
    assert result.prediction_dice == 1.0

    assert (
        result.prediction_volume_error
        == 0.0
    )

    assert (
        result.persistence_dice
        < result.prediction_dice
    )

    assert (
        manifest_path.read_bytes()
        == manifest_before
    )


def test_frozen_protocol_rejects_noncanonical_sequence(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        name="baseline",
        day=0.0,
        active=(
            (2, 2, 2),
        ),
    )

    t1 = make_timepoint(
        name="t1",
        day=60.0,
        active=(
            (2, 2, 2),
        ),
    )

    with pytest.raises(
        ValueError,
        match="t0 -> t1 -> t2",
    ):
        freeze_v2_prediction(
            start=t0,
            observed=t1,
            target=make_target(),
            treatment=None,
            config=make_config(),
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "artifact",
        )


def test_frozen_protocol_rejects_target_before_observation(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        name="t0",
        day=0.0,
        active=(
            (2, 2, 2),
        ),
    )

    t1 = make_timepoint(
        name="t1",
        day=60.0,
        active=(
            (2, 2, 2),
        ),
    )

    target = PredictionTarget(
        timepoint_name="t2",
        target_day=60.0,
    )

    with pytest.raises(
        ValueError,
        match="must occur after",
    ):
        freeze_v2_prediction(
            start=t0,
            observed=t1,
            target=target,
            treatment=None,
            config=make_config(),
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "artifact",
        )


def test_manifest_is_valid_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _, _ = build_artifact(
        monkeypatch,
        tmp_path,
    )

    manifest_path = (
        artifact.directory
        / "manifest.json"
    )

    payload: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )

    assert payload == artifact.manifest