from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.post_rt_selection as selection_module
from gbm_twin.calibration.diagnostics import CalibrationDiagnostics
from gbm_twin.calibration.grid_search import CalibrationResult
from gbm_twin.data.cfb_treatment import TreatmentRecord
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.evaluation.cohort import EvaluationConfig
from gbm_twin.evaluation.config import CohortExperimentConfig
from gbm_twin.models.solver import TreatmentModel
from gbm_twin.models.treatment import RadiotherapyProtocol
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    V2CalibrationRun,
)
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.post_rt_selection import (
    select_post_rt_parameters,
)
from gbm_twin.workflows.repository import RepositoryState


def make_volume(name: str) -> NiftiVolume:
    data = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )
    data[2, 2, 2] = 1.0

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


def make_timepoint(
    *,
    name: str,
    day: float,
) -> PreparedPatientTimepoint:
    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=make_volume(
            f"{name}_t1gd.nii.gz"
        ),
        gtv=make_volume(
            f"{name}_gtv.nii.gz"
        ),
        brain_mask=make_volume(
            f"{name}_brain.nii.gz"
        ),
    )


def make_experiment(
    tmp_path: Path,
) -> CohortExperimentConfig:
    return CohortExperimentConfig(
        patient_ids=(42,),
        metadata_root=tmp_path / "metadata",
        patients_root=tmp_path / "patients",
        evaluation=EvaluationConfig(
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
            threshold=0.5,
            dt=2.0,
            diffusion_values=(
                0.0,
                0.01,
            ),
            proliferation_values=(
                0.0,
                0.01,
            ),
            volume_weight=0.5,
            refinement_rounds=1,
            upper_boundary_expansion_factor=0.5,
        ),
        trajectory_stable_threshold=0.1,
        raw_output_csv=tmp_path / "raw.csv",
        analyzed_output_csv=tmp_path / "analyzed.csv",
    )


class FakeTreatmentMetadata:
    def __init__(
        self,
        metadata_root: Path,
    ) -> None:
        self.metadata_root = metadata_root

    def treatment(
        self,
        patient_id: int,
    ) -> TreatmentRecord | None:
        assert patient_id == 42

        return TreatmentRecord(
            patient_id=42,
            delay_t0_to_radiotherapy_weeks=1.0,
            dose_gy=60.0,
            fractions_number=30,
        )


def make_calibration_run(
    *,
    loss: float,
) -> V2CalibrationRun:
    best = CalibrationResult(
        diffusion=0.01,
        proliferation=0.01,
        dice=1.0 - loss,
        volume_error=0.0,
        loss=loss,
    )

    return V2CalibrationRun(
        patient_id=42,
        start_timepoint="t0",
        observed_timepoint="t1",
        start_day=0.0,
        observed_day=100.0,
        duration_days=100.0,
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
        refined_proliferation_values=(0.01,),
    )


def test_post_rt_selection_uses_t0_t1_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment_config = (
        tmp_path
        / "experiment.yaml"
    )
    experiment_config.write_text(
        "test: true\n",
        encoding="utf-8",
    )

    selection_config = (
        tmp_path
        / "post_rt.yaml"
    )
    selection_config.write_text(
        """
schema_version: 1
initial_kill_rates_per_day:
  - 0.005
decay_times_days:
  - 60.0
include_fractionated_only_baseline: true
""".lstrip(),
        encoding="utf-8",
    )

    def fake_load_experiment(
        path: Path,
    ) -> CohortExperimentConfig:
        assert path == experiment_config
        return make_experiment(
            tmp_path
        )

    def fake_repository_state(
        path: Path,
    ) -> RepositoryState:
        assert path == tmp_path
        return RepositoryState(
            commit_sha="a" * 40,
            dirty=False,
        )

    monkeypatch.setattr(
        selection_module,
        "load_cohort_experiment_config",
        fake_load_experiment,
    )
    monkeypatch.setattr(
        selection_module,
        "read_repository_state",
        fake_repository_state,
    )
    monkeypatch.setattr(
        selection_module,
        "CFBTreatmentMetadata",
        FakeTreatmentMetadata,
    )

    requested_timepoints: list[str] = []

    def fake_prepare_patient_timepoint(
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
        assert target_spacing == (
            2.0,
            2.0,
            2.0,
        )

        requested_timepoints.append(
            timepoint_name
        )

        if timepoint_name == "t0":
            return make_timepoint(
                name="t0",
                day=0.0,
            )

        if timepoint_name == "t1":
            return make_timepoint(
                name="t1",
                day=100.0,
            )

        raise AssertionError(
            "Post-RT selection must not load t2"
        )

    monkeypatch.setattr(
        selection_module,
        "prepare_patient_timepoint",
        fake_prepare_patient_timepoint,
    )

    def fake_calibrate_v2_interval(
        *,
        start: PreparedPatientTimepoint,
        observed: PreparedPatientTimepoint,
        treatment: TreatmentModel | None,
        config: V2CalibrationConfig,
        cache_dir: Path,
        workers: int = 1,
    ) -> V2CalibrationRun:
        assert start.name == "t0"
        assert observed.name == "t1"
        assert workers == 2
        assert config.refinement_rounds == 1
        assert cache_dir.name == "patient-42"

        loss = (
            0.1
            if isinstance(
                treatment,
                RadiotherapyProtocol,
            )
            else 0.2
        )

        return make_calibration_run(
            loss=loss
        )

    monkeypatch.setattr(
        selection_module,
        "calibrate_v2_interval",
        fake_calibrate_v2_interval,
    )

    output_dir = (
        tmp_path
        / "selection"
    )

    result = select_post_rt_parameters(
        experiment_config_path=(
            experiment_config
        ),
        selection_config_path=(
            selection_config
        ),
        repo_root=tmp_path,
        cache_root=tmp_path / "cache",
        output_dir=output_dir,
        workers=2,
    )

    assert requested_timepoints == [
        "t0",
        "t1",
    ]

    leakage = result.manifest[
        "leakage_control"
    ]
    assert isinstance(
        leakage,
        dict,
    )
    assert leakage[
        "loads_t2_imaging"
    ] is False

    selected = result.manifest[
        "selected_candidate"
    ]
    assert isinstance(
        selected,
        dict,
    )
    assert selected[
        "candidate_id"
    ] == "post-rt-k0.005-tau60"

    assert (
        output_dir
        / "post_rt_selection.json"
    ).is_file()
    assert (
        output_dir
        / "post_rt_selection.sha256"
    ).is_file()
    assert (
        output_dir
        / "post_rt_candidates.csv"
    ).is_file()
    assert (
        output_dir
        / "post_rt_patients.csv"
    ).is_file()
