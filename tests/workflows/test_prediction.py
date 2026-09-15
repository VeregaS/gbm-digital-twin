import json
from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.prediction as prediction_module
from gbm_twin.calibration.grid_search import CalibrationResult
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.evaluation.frozen_prediction import evaluate_frozen_v2_prediction
from gbm_twin.models.treatment import PIRTFractionatedRadiotherapy
from gbm_twin.workflows.calibration import V2CalibrationConfig, V2CalibrationRun
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.prediction import (
    V2_ASSIMILATION_RULE,
    freeze_v2_prediction,
    load_frozen_v2_prediction,
)


def make_volume(name: str, active: tuple[tuple[int, int, int], ...]) -> NiftiVolume:
    data = np.zeros((5, 5, 5), dtype=np.float32)

    for index in active:
        data[index] = 1.0

    return NiftiVolume(
        path=Path(name),
        data=data,
        affine=np.eye(4, dtype=np.float64),
        spacing=(2.0, 2.0, 2.0),
    )


def make_timepoint(
    *,
    name: str,
    day: float,
    active: tuple[tuple[int, int, int], ...],
) -> PreparedPatientTimepoint:
    brain = make_volume(
        f"{name}_brain.nii.gz",
        tuple(np.ndindex((5, 5, 5))),
    )

    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=make_volume(f"{name}_t1gd.nii.gz", active),
        gtv=make_volume(f"{name}_gtv.nii.gz", active),
        brain_mask=brain,
    )


def make_config() -> V2CalibrationConfig:
    return V2CalibrationConfig(
        diffusion_values=(0.01, 0.03, 0.05),
        proliferation_values=(0.005, 0.015, 0.025),
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
        refined_diffusion_values=(0.02, 0.03, 0.04),
        refined_proliferation_values=(0.01, 0.015, 0.02),
    )


def build_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    treatment: PIRTFractionatedRadiotherapy | None = None,
):
    t0 = make_timepoint(name="t0", day=0.0, active=((2, 2, 2),))
    t1 = make_timepoint(
        name="t1",
        day=60.0,
        active=((2, 2, 2), (2, 2, 3)),
    )
    predicted_field = np.zeros((5, 5, 5), dtype=np.float32)
    predicted_field[2, 2, 2] = 0.9
    predicted_field[2, 2, 3] = 0.8
    predicted_field[2, 3, 3] = 0.7

    captured: dict[str, object] = {"calibration_calls": 0}

    def fake_calibration(**kwargs):
        captured["calibration_calls"] = int(captured["calibration_calls"]) + 1
        captured["calibration_kwargs"] = kwargs
        return make_calibration_run()

    def fake_simulation(initial_field, params, **kwargs):
        captured["initial_field"] = initial_field
        captured["params"] = params
        captured["simulation_kwargs"] = kwargs
        return predicted_field.copy()

    monkeypatch.setattr(prediction_module, "calibrate_v2_interval", fake_calibration)
    monkeypatch.setattr(prediction_module, "simulate_reaction_diffusion", fake_simulation)

    output_dir = tmp_path / "patient-42-t1-to-t2"
    artifact = freeze_v2_prediction(
        start=t0,
        observed=t1,
        target_timepoint="t2",
        target_day=120.0,
        treatment=treatment,
        config=make_config(),
        cache_dir=tmp_path / "cache",
        output_dir=output_dir,
        workers=2,
    )

    return artifact, captured, t0, t1


def test_freeze_v2_prediction_seals_protocol_before_t2_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, captured, t0, t1 = build_artifact(monkeypatch, tmp_path)
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
    assert manifest["parameters"]["diffusion"] == 0.03
    assert manifest["parameters"]["proliferation"] == 0.015
    assert manifest["parameters"]["assimilation_rule"] == V2_ASSIMILATION_RULE
    assert captured["calibration_kwargs"]["start"] is t0
    assert captured["calibration_kwargs"]["observed"] is t1
    assert captured["simulation_kwargs"]["start_time_day"] == 60.0
    assert captured["simulation_kwargs"]["duration_days"] == 60.0
    assert np.count_nonzero(artifact.prediction_mask) == 3
    assert set(path.name for path in artifact.directory.iterdir()) == {
        "manifest.json",
        "manifest.sha256",
        "prediction_field.npy",
        "prediction_mask.npy",
        "persistence_mask.npy",
        "volume_baseline_mask.npy",
    }

    with pytest.raises(FileExistsError, match="already exists"):
        freeze_v2_prediction(
            start=t0,
            observed=t1,
            target_timepoint="t2",
            target_day=120.0,
            treatment=None,
            config=make_config(),
            cache_dir=tmp_path / "cache",
            output_dir=artifact.directory,
        )

    assert captured["calibration_calls"] == 1


def test_load_frozen_prediction_rejects_modified_array(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _ = build_artifact(monkeypatch, tmp_path)
    path = artifact.directory / "prediction_mask.npy"
    modified = np.zeros((5, 5, 5), dtype=np.uint8)
    np.save(path, modified, allow_pickle=False)

    with pytest.raises(ValueError, match="checksum mismatch"):
        load_frozen_v2_prediction(artifact.directory)


def test_freeze_records_complete_pirt_protocol(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    treatment = PIRTFractionatedRadiotherapy(
        fraction_days=(10.0, 11.0),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.01,
        beta_per_gy2=0.001,
    )
    artifact, captured, _, _ = build_artifact(
        monkeypatch,
        tmp_path,
        treatment,
    )

    assert artifact.manifest["treatment"] == {
        "kind": "pirt_fractionated_radiotherapy",
        "fraction_days": [10.0, 11.0],
        "dose_per_fraction_gy": 2.0,
        "alpha_per_gy": 0.01,
        "beta_per_gy2": 0.001,
    }
    assert captured["calibration_kwargs"]["treatment"] is treatment
    assert captured["simulation_kwargs"]["treatment"] is treatment


def test_load_frozen_prediction_rejects_modified_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _ = build_artifact(monkeypatch, tmp_path)
    path = artifact.directory / "manifest.json"
    path.write_text(path.read_text() + " ", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest checksum mismatch"):
        load_frozen_v2_prediction(artifact.directory)


def test_evaluator_receives_t2_only_after_artifact_is_frozen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _ = build_artifact(monkeypatch, tmp_path)
    manifest_before = (artifact.directory / "manifest.json").read_bytes()
    t2 = make_timepoint(
        name="t2",
        day=120.0,
        active=((2, 2, 2), (2, 2, 3), (2, 3, 3)),
    )

    result = evaluate_frozen_v2_prediction(
        artifact_dir=artifact.directory,
        observed_target=t2,
    )

    assert result.patient_id == 42
    assert result.prediction_dice == 1.0
    assert result.prediction_volume_error == 0.0
    assert result.persistence_dice < result.prediction_dice
    assert (artifact.directory / "manifest.json").read_bytes() == manifest_before


def test_frozen_protocol_rejects_noncanonical_sequence(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(name="baseline", day=0.0, active=((2, 2, 2),))
    t1 = make_timepoint(name="t1", day=60.0, active=((2, 2, 2),))

    with pytest.raises(ValueError, match="t0 -> t1 -> t2"):
        freeze_v2_prediction(
            start=t0,
            observed=t1,
            target_timepoint="t2",
            target_day=120.0,
            treatment=None,
            config=make_config(),
            cache_dir=tmp_path / "cache",
            output_dir=tmp_path / "artifact",
        )


def test_manifest_is_valid_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    artifact, _, _, _ = build_artifact(monkeypatch, tmp_path)
    payload = json.loads((artifact.directory / "manifest.json").read_text())

    assert payload == artifact.manifest
