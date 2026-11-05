from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.prediction as prediction_module
from gbm_twin.calibration.diagnostics import CalibrationDiagnostics
from gbm_twin.calibration.grid_search import CalibrationResult
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import TreatmentModel
from gbm_twin.models.treatment import (
    PIRTFractionatedRadiotherapy,
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    V2CalibrationRun,
)
from gbm_twin.workflows.contracts import PredictionTarget
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.post_rt_selection_artifact import (
    SelectedPostRTCandidate,
)
from gbm_twin.workflows.prediction import (
    V3_FROZEN_PROTOCOL_VERSION,
    freeze_v3_prediction,
    load_frozen_v2_prediction,
    load_frozen_v3_prediction,
)
from gbm_twin.workflows.provenance import (
    InputFileProvenance,
    PredictionProvenance,
)


def _volume(
    path: Path,
    *,
    active: tuple[tuple[int, int, int], ...],
    brain: bool = False,
) -> NiftiVolume:
    data = (
        np.ones((5, 5, 5), dtype=np.float32)
        if brain
        else np.zeros((5, 5, 5), dtype=np.float32)
    )
    if not brain:
        for index in active:
            data[index] = 1.0

    return NiftiVolume(
        path=path,
        data=data,
        affine=np.eye(4, dtype=np.float64),
        spacing=(2.0, 2.0, 2.0),
    )


def _timepoint(
    tmp_path: Path,
    *,
    name: str,
    day: float,
    active: tuple[tuple[int, int, int], ...],
) -> PreparedPatientTimepoint:
    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=_volume(
            tmp_path / f"{name}_t1gd.nii.gz",
            active=active,
        ),
        gtv=_volume(
            tmp_path / f"{name}_gtv.nii.gz",
            active=active,
        ),
        brain_mask=_volume(
            tmp_path / f"{name}_brain.nii.gz",
            active=(),
            brain=True,
        ),
    )


def _provenance() -> PredictionProvenance:
    return PredictionProvenance(
        dataset_name="CFB-GBM",
        dataset_version=4,
        dataset_doi="10.7937/v9pn-2f72",
        git_commit_sha="a" * 40,
        git_dirty=False,
        config_sha256="b" * 64,
        inputs=(
            InputFileProvenance(
                logical_name="t0_gtv",
                filename="t0_gtv.nii.gz",
                sha256="c" * 64,
            ),
        ),
    )


def _calibration_run() -> V2CalibrationRun:
    best = CalibrationResult(
        diffusion=0.01,
        proliferation=0.005,
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
        diagnostics=CalibrationDiagnostics(
            diffusion_at_boundary=False,
            proliferation_at_boundary=False,
            diffusion_bracketed=True,
            proliferation_bracketed=True,
            identifiable=True,
        ),
        candidates=(best,),
        coarse_candidates=(best,),
        refined_candidates=(best,),
        refined_diffusion_values=(0.01,),
        refined_proliferation_values=(0.005,),
    )


def test_freeze_v3_prediction_records_selected_post_rt_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    start = _timepoint(
        tmp_path,
        name="t0",
        day=0.0,
        active=((2, 2, 2),),
    )
    observed = _timepoint(
        tmp_path,
        name="t1",
        day=60.0,
        active=((2, 2, 2), (2, 2, 3)),
    )

    fractions = PIRTFractionatedRadiotherapy(
        fraction_days=(10.0, 11.0),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.01,
        beta_per_gy2=0.001,
    )
    treatment = RadiotherapyProtocol(
        fractions=fractions,
        post_effect=PostRadiotherapyEffect(
            start_day=11.0,
            initial_kill_rate=0.005,
            decay_time_days=60.0,
        ),
    )
    selection = SelectedPostRTCandidate(
        candidate_id="post-rt-k0.005-tau60",
        initial_kill_rate_per_day=0.005,
        decay_time_days=60.0,
        source_manifest_sha256="d" * 64,
        selection_config_sha256="e" * 64,
        experiment_config_sha256="f" * 64,
    )

    captured_treatments: list[TreatmentModel | None] = []

    def fake_calibration(
        *,
        start: PreparedPatientTimepoint,
        observed: PreparedPatientTimepoint,
        treatment: TreatmentModel | None,
        config: V2CalibrationConfig,
        cache_dir: Path,
        workers: int = 1,
    ) -> V2CalibrationRun:
        captured_treatments.append(treatment)
        return _calibration_run()

    def fake_simulation(
        initial_field: np.ndarray,
        params: ReactionDiffusionParameters,
        *,
        spacing: tuple[float, float, float],
        duration_days: float,
        dt: float,
        domain_mask: np.ndarray | None = None,
        treatment: TreatmentModel | None = None,
        start_time_day: float = 0.0,
        crop_to_domain: bool = True,
    ) -> np.ndarray:
        captured_treatments.append(treatment)
        return initial_field.copy()

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

    artifact = freeze_v3_prediction(
        start=start,
        observed=observed,
        target=PredictionTarget(
            timepoint_name="t2",
            target_day=120.0,
        ),
        provenance=_provenance(),
        treatment=treatment,
        model_selection=selection,
        config=V2CalibrationConfig(
            diffusion_values=(0.0, 0.01),
            proliferation_values=(0.0, 0.005),
        ),
        cache_dir=tmp_path / "cache",
        output_dir=tmp_path / "frozen-v3",
        workers=2,
    )

    manifest = artifact.manifest
    assert manifest["model_version"] == "V3"
    assert manifest["protocol_version"] == V3_FROZEN_PROTOCOL_VERSION
    assert manifest["model_selection"] == selection.to_provenance_payload()

    treatment_payload = manifest["treatment"]
    assert treatment_payload["kind"] == "radiotherapy_protocol"
    assert treatment_payload["post_rt_effect"] == {
        "start_day": 11.0,
        "initial_kill_rate_per_day": 0.005,
        "decay_time_days": 60.0,
    }

    assert captured_treatments == [treatment, treatment]
    loaded = load_frozen_v3_prediction(artifact.directory)
    assert loaded.manifest == artifact.manifest

    with pytest.raises(
        ValueError,
        match="V2",
    ):
        load_frozen_v2_prediction(artifact.directory)
