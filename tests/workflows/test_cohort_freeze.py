from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.cohort_freeze as cohort_module
from gbm_twin.data.dataset_manifest import CFBDatasetManifest
from gbm_twin.evaluation.cohort import EvaluationConfig
from gbm_twin.evaluation.config import CohortExperimentConfig
from gbm_twin.workflows.calibration import V2CalibrationConfig
from gbm_twin.workflows.cohort_freeze import freeze_cohort_from_configs
from gbm_twin.workflows.eligibility import (
    EligibilityIssue,
    EligibilityReason,
    PatientEligibility,
)
from gbm_twin.workflows.post_rt_selection_artifact import (
    SelectedPostRTCandidate,
)
from gbm_twin.workflows.prediction import FrozenPredictionArtifact
from gbm_twin.workflows.repository import RepositoryState

GIT_SHA = (
    "0123456789abcdef"
    "0123456789abcdef"
    "01234567"
)


def make_experiment(tmp_path: Path) -> CohortExperimentConfig:
    return CohortExperimentConfig(
        patient_ids=(42, 108),
        metadata_root=tmp_path / "metadata",
        patients_root=tmp_path / "patients",
        evaluation=EvaluationConfig(
            target_spacing=(2.0, 2.0, 2.0),
            threshold=0.5,
            dt=2.0,
            diffusion_values=(0.0, 0.005, 0.015, 0.03),
            proliferation_values=(0.0, 0.015, 0.035, 0.055),
            volume_weight=0.5,
        ),
        trajectory_stable_threshold=0.1,
        raw_output_csv=tmp_path / "raw.csv",
        analyzed_output_csv=tmp_path / "analyzed.csv",
    )


def make_manifest() -> CFBDatasetManifest:
    return CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source="The Cancer Imaging Archive",
        license="CC BY 4.0",
        expected_subjects=264,
        metadata_patterns=(
            "CFB-GBM_mri_availability_*.tsv",
            "CFB-GBM_rano_criteria_*.tsv",
            "CFB-GBM_treatment_imaging_availability_*.tsv",
        ),
        required_timepoints=("t0", "t1", "t2"),
        required_modalities=("t1gd",),
        required_patient_files=(
            "{patient_id}_{timepoint}_t1gd.nii.gz",
            "{patient_id}_{timepoint}_gtv.nii.gz",
            "{patient_id}_{timepoint}_brain_mask.nii.gz",
        ),
    )


def make_artifact(directory: Path) -> FrozenPredictionArtifact:
    directory.mkdir(parents=True)
    field = np.zeros((2, 2, 2), dtype=np.float32)
    mask = np.zeros((2, 2, 2), dtype=bool)
    return FrozenPredictionArtifact(
        directory=directory,
        manifest={"sealed": True},
        prediction_field=field,
        prediction_mask=mask,
        persistence_mask=mask.copy(),
        volume_baseline_mask=mask.copy(),
    )


def eligible(patient_id: int) -> PatientEligibility:
    return PatientEligibility(
        patient_id=patient_id,
        issues=(),
    )


def excluded(patient_id: int) -> PatientEligibility:
    return PatientEligibility(
        patient_id=patient_id,
        issues=(
            EligibilityIssue(
                reason=EligibilityReason.TREATMENT_SCHEDULE_UNAVAILABLE,
                detail="Treatment schedule is unavailable",
            ),
        ),
    )


def test_freeze_cohort_freezes_only_eligible_patients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment = make_experiment(tmp_path)
    dataset_manifest = make_manifest()
    frozen_patient_ids: list[int] = []

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
            assert metadata_root == experiment.metadata_root
            assert patients_root == experiment.patients_root
            assert dataset_manifest is dataset_manifest
            assert git_commit_sha == GIT_SHA
            assert not git_dirty
            assert target_spacing == (2.0, 2.0, 2.0)
            assert post_rt_selection is None
            assert calibration_config.diffusion_values

        def assess_eligibility(
            self,
            patient_id: int,
        ) -> PatientEligibility:
            if patient_id == 42:
                return eligible(patient_id)
            return excluded(patient_id)

        def freeze_patient(
            self,
            *,
            patient_id: int,
            cache_dir: Path,
            output_dir: Path,
            workers: int = 1,
        ) -> FrozenPredictionArtifact:
            frozen_patient_ids.append(patient_id)
            assert workers == 2
            assert cache_dir.name == "patient-42"
            return make_artifact(output_dir)

    monkeypatch.setattr(
        cohort_module,
        "load_cohort_experiment_config",
        lambda path: experiment,
    )
    monkeypatch.setattr(
        cohort_module,
        "load_cfb_dataset_manifest",
        lambda path: dataset_manifest,
    )
    monkeypatch.setattr(
        cohort_module,
        "read_repository_state",
        lambda path: RepositoryState(
            commit_sha=GIT_SHA,
            dirty=False,
        ),
    )
    monkeypatch.setattr(
        cohort_module,
        "PatientTwinService",
        FakePatientTwinService,
    )

    output_root = tmp_path / "cohort-freeze"
    result = freeze_cohort_from_configs(
        experiment_config_path=tmp_path / "experiment.yaml",
        dataset_manifest_path=tmp_path / "dataset.yaml",
        repo_root=tmp_path,
        cache_root=tmp_path / "cache",
        output_root=output_root,
        workers=2,
    )

    assert frozen_patient_ids == [42]
    assert result.frozen_patient_ids == (42,)
    assert result.excluded_patient_ids == (108,)
    assert result.directory.is_dir()
    assert (result.directory / "cohort_manifest.json").is_file()
    assert (result.directory / "cohort_manifest.sha256").is_file()
    assert (
        result.manifest["frozen_patients"][0]["artifact_dir"]
        == "patients/patient-42/frozen-v2"
    )
    assert (
        result.manifest["excluded_patients"][0]["issues"][0]["reason"]
        == "treatment_schedule_unavailable"
    )


def test_freeze_cohort_rejects_dirty_repository(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        cohort_module,
        "load_cohort_experiment_config",
        lambda path: make_experiment(tmp_path),
    )
    monkeypatch.setattr(
        cohort_module,
        "load_cfb_dataset_manifest",
        lambda path: make_manifest(),
    )
    monkeypatch.setattr(
        cohort_module,
        "read_repository_state",
        lambda path: RepositoryState(
            commit_sha=GIT_SHA,
            dirty=True,
        ),
    )

    with pytest.raises(
        ValueError,
        match="clean Git working tree",
    ):
        freeze_cohort_from_configs(
            experiment_config_path=tmp_path / "experiment.yaml",
            dataset_manifest_path=tmp_path / "dataset.yaml",
            repo_root=tmp_path,
            cache_root=tmp_path / "cache",
            output_root=tmp_path / "cohort-freeze",
        )


def test_failed_freeze_is_not_published(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment = make_experiment(tmp_path)

    class FailingPatientTwinService:
        def __init__(
            self,
            **kwargs: object,
        ) -> None:
            assert kwargs

        def assess_eligibility(
            self,
            patient_id: int,
        ) -> PatientEligibility:
            return eligible(patient_id)

        def freeze_patient(
            self,
            *,
            patient_id: int,
            cache_dir: Path,
            output_dir: Path,
            workers: int = 1,
        ) -> FrozenPredictionArtifact:
            raise RuntimeError("synthetic calibration failure")

    monkeypatch.setattr(
        cohort_module,
        "load_cohort_experiment_config",
        lambda path: experiment,
    )
    monkeypatch.setattr(
        cohort_module,
        "load_cfb_dataset_manifest",
        lambda path: make_manifest(),
    )
    monkeypatch.setattr(
        cohort_module,
        "read_repository_state",
        lambda path: RepositoryState(
            commit_sha=GIT_SHA,
            dirty=False,
        ),
    )
    monkeypatch.setattr(
        cohort_module,
        "PatientTwinService",
        FailingPatientTwinService,
    )

    output_root = tmp_path / "cohort-freeze"
    with pytest.raises(
        RuntimeError,
        match="synthetic calibration failure",
    ):
        freeze_cohort_from_configs(
            experiment_config_path=tmp_path / "experiment.yaml",
            dataset_manifest_path=tmp_path / "dataset.yaml",
            repo_root=tmp_path,
            cache_root=tmp_path / "cache",
            output_root=output_root,
        )

    assert not output_root.exists()
