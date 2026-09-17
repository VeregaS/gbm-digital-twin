from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.cohort_freeze as cohort_module
from gbm_twin.data.dataset_manifest import CFBDatasetManifest
from gbm_twin.evaluation.cohort import EvaluationConfig
from gbm_twin.evaluation.config import CohortExperimentConfig
from gbm_twin.workflows.calibration import V2CalibrationConfig
from gbm_twin.workflows.cohort_freeze import (
    freeze_v3_cohort_from_configs,
)
from gbm_twin.workflows.eligibility import PatientEligibility
from gbm_twin.workflows.post_rt_selection_artifact import (
    SelectedPostRTCandidate,
)
from gbm_twin.workflows.prediction import FrozenPredictionArtifact
from gbm_twin.workflows.repository import RepositoryState


def _experiment(tmp_path: Path) -> CohortExperimentConfig:
    return CohortExperimentConfig(
        patient_ids=(42,),
        metadata_root=tmp_path / "metadata",
        patients_root=tmp_path / "patients",
        evaluation=EvaluationConfig(
            diffusion_values=(0.0, 0.01),
            proliferation_values=(0.0, 0.01),
            refinement_rounds=3,
            upper_boundary_expansion_factor=1.0,
        ),
        trajectory_stable_threshold=0.1,
        raw_output_csv=tmp_path / "raw.csv",
        analyzed_output_csv=tmp_path / "analyzed.csv",
    )


def _dataset() -> CFBDatasetManifest:
    return CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source="TCIA",
        license="CC BY 4.0",
        expected_subjects=264,
        metadata_patterns=("*.tsv",),
        required_timepoints=("t0", "t1", "t2"),
        required_modalities=("t1gd",),
        required_patient_files=("{patient_id}_{timepoint}.nii.gz",),
    )


def _selection() -> SelectedPostRTCandidate:
    return SelectedPostRTCandidate(
        candidate_id="post-rt-k0.005-tau60",
        initial_kill_rate_per_day=0.005,
        decay_time_days=60.0,
        source_manifest_sha256="a" * 64,
        selection_config_sha256="b" * 64,
        experiment_config_sha256="c" * 64,
    )


def _artifact(directory: Path) -> FrozenPredictionArtifact:
    directory.mkdir(parents=True)
    field = np.zeros((2, 2, 2), dtype=np.float32)
    mask = np.zeros((2, 2, 2), dtype=bool)
    return FrozenPredictionArtifact(
        directory=directory,
        manifest={"model_version": "V3", "sealed": True},
        prediction_field=field,
        prediction_mask=mask,
        persistence_mask=mask.copy(),
        volume_baseline_mask=mask.copy(),
    )


def test_v3_cohort_freeze_uses_sealed_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment = _experiment(tmp_path)
    selected = _selection()
    captured_selection: list[SelectedPostRTCandidate | None] = []

    class FakePatientTwinService:
        def __init__(
            self,
            *,
            metadata_root: Path,
            patients_root: Path,
            dataset_manifest: CFBDatasetManifest,
            calibration_config: V2CalibrationConfig,
            git_commit_sha: str,
            git_dirty: bool,
            target_spacing: tuple[float, float, float],
            post_rt_selection: SelectedPostRTCandidate | None = None,
        ) -> None:
            captured_selection.append(post_rt_selection)
            assert post_rt_selection is selected
            assert calibration_config.refinement_rounds == 3

        def assess_eligibility(
            self,
            patient_id: int,
        ) -> PatientEligibility:
            return PatientEligibility(
                patient_id=patient_id,
                issues=(),
            )

        def freeze_patient(
            self,
            *,
            patient_id: int,
            cache_dir: Path,
            output_dir: Path,
            workers: int = 1,
        ) -> FrozenPredictionArtifact:
            assert patient_id == 42
            return _artifact(output_dir)

    def fake_load_selection(
        *,
        selection_root: Path,
        experiment_config_path: Path,
    ) -> SelectedPostRTCandidate:
        assert selection_root == tmp_path / "selection"
        return selected

    def fake_load_experiment(
        path: Path,
    ) -> CohortExperimentConfig:
        return experiment

    def fake_load_dataset(
        path: Path,
    ) -> CFBDatasetManifest:
        return _dataset()

    def fake_repository_state(
        path: Path,
    ) -> RepositoryState:
        return RepositoryState(
            commit_sha="d" * 40,
            dirty=False,
        )

    monkeypatch.setattr(
        cohort_module,
        "load_selected_post_rt_candidate",
        fake_load_selection,
    )
    monkeypatch.setattr(
        cohort_module,
        "load_cohort_experiment_config",
        fake_load_experiment,
    )
    monkeypatch.setattr(
        cohort_module,
        "load_cfb_dataset_manifest",
        fake_load_dataset,
    )
    monkeypatch.setattr(
        cohort_module,
        "read_repository_state",
        fake_repository_state,
    )
    monkeypatch.setattr(
        cohort_module,
        "PatientTwinService",
        FakePatientTwinService,
    )

    result = freeze_v3_cohort_from_configs(
        experiment_config_path=tmp_path / "experiment.yaml",
        dataset_manifest_path=tmp_path / "dataset.yaml",
        post_rt_selection_root=tmp_path / "selection",
        repo_root=tmp_path,
        cache_root=tmp_path / "cache",
        output_root=tmp_path / "v3-freeze",
        workers=2,
    )

    assert captured_selection == [selected]
    assert result.manifest["kind"] == "v3_cohort_freeze"
    assert (
        result.manifest["frozen_patients"][0]["artifact_dir"]
        == "patients/patient-42/frozen-v3"
    )

    model = result.manifest["model"]
    assert model["version"] == "V3"
    assert model["post_rt_candidate_id"] == selected.candidate_id
    assert model["post_rt_selection_manifest_sha256"] == "a" * 64
