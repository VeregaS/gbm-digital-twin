from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.single_patient as single_patient_module
from gbm_twin.data.dataset_manifest import (
    CFBDatasetManifest,
)
from gbm_twin.evaluation.cohort import (
    EvaluationConfig,
)
from gbm_twin.evaluation.config import (
    CohortExperimentConfig,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)
from gbm_twin.workflows.repository import (
    RepositoryState,
)
from gbm_twin.workflows.single_patient import (
    calibration_config_from_experiment,
    freeze_patient_from_configs,
)

GIT_SHA = (
    "0123456789abcdef"
    "0123456789abcdef"
    "01234567"
)


@dataclass
class CapturedService:
    metadata_root: Path | None = None
    patients_root: Path | None = None
    calibration_config: (
        V2CalibrationConfig | None
    ) = None
    git_commit_sha: str | None = None
    git_dirty: bool | None = None
    target_spacing: (
        tuple[float, float, float]
        | None
    ) = None
    patient_id: int | None = None
    cache_dir: Path | None = None
    output_dir: Path | None = None
    workers: int | None = None


def make_experiment(
    tmp_path: Path,
) -> CohortExperimentConfig:
    return CohortExperimentConfig(
        patient_ids=(
            42,
            108,
        ),
        metadata_root=(
            tmp_path
            / "metadata"
        ),
        patients_root=(
            tmp_path
            / "patients"
        ),
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
                0.005,
                0.015,
                0.03,
            ),
            proliferation_values=(
                0.0,
                0.015,
                0.035,
                0.055,
            ),
            volume_weight=0.5,
        ),
        trajectory_stable_threshold=0.1,
        raw_output_csv=(
            tmp_path
            / "raw.csv"
        ),
        analyzed_output_csv=(
            tmp_path
            / "analyzed.csv"
        ),
    )


def make_manifest() -> CFBDatasetManifest:
    return CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source=(
            "The Cancer Imaging Archive"
        ),
        license="CC BY 4.0",
        expected_subjects=264,
        metadata_patterns=(
            (
                "CFB-GBM_"
                "mri_availability_*.tsv"
            ),
            (
                "CFB-GBM_"
                "rano_criteria_*.tsv"
            ),
            (
                "CFB-GBM_treatment_"
                "imaging_availability_*.tsv"
            ),
        ),
        required_timepoints=(
            "t0",
            "t1",
            "t2",
        ),
        required_modalities=(
            "t1gd",
        ),
        required_patient_files=(
            (
                "{patient_id}_"
                "{timepoint}_t1gd.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_gtv.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_brain_mask.nii.gz"
            ),
        ),
    )


def make_artifact(
    output_dir: Path,
) -> FrozenV2PredictionArtifact:
    field = np.zeros(
        (2, 2, 2),
        dtype=np.float32,
    )

    mask = np.zeros(
        (2, 2, 2),
        dtype=bool,
    )

    return FrozenV2PredictionArtifact(
        directory=output_dir,
        manifest={
            "sealed": True,
        },
        prediction_field=field,
        prediction_mask=mask,
        persistence_mask=mask.copy(),
        volume_baseline_mask=mask.copy(),
    )


def test_calibration_config_comes_from_experiment(
    tmp_path: Path,
) -> None:
    result = (
        calibration_config_from_experiment(
            make_experiment(
                tmp_path
            )
        )
    )

    assert result.diffusion_values == (
        0.0,
        0.005,
        0.015,
        0.03,
    )

    assert (
        result.proliferation_values
        == (
            0.0,
            0.015,
            0.035,
            0.055,
        )
    )

    assert result.dt_days == 2.0
    assert result.observation_threshold == 0.5
    assert result.volume_weight == 0.5


def test_freeze_patient_from_configs_wires_service(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment = make_experiment(
        tmp_path
    )

    manifest = make_manifest()

    captured = CapturedService()

    def fake_load_experiment(
        path: Path,
    ) -> CohortExperimentConfig:
        assert path == (
            tmp_path
            / "experiment.yaml"
        )

        return experiment

    def fake_load_manifest(
        path: Path,
    ) -> CFBDatasetManifest:
        assert path == (
            tmp_path
            / "dataset.yaml"
        )

        return manifest

    def fake_repository_state(
        repo_root: Path,
    ) -> RepositoryState:
        assert repo_root == tmp_path

        return RepositoryState(
            commit_sha=GIT_SHA,
            dirty=False,
        )

    class FakePatientTwinService:
        def __init__(
            self,
            *,
            metadata_root: Path,
            patients_root: Path,
            dataset_manifest: (
                CFBDatasetManifest
            ),
            calibration_config: (
                V2CalibrationConfig
            ),
            git_commit_sha: str,
            git_dirty: bool,
            target_spacing: tuple[
                float,
                float,
                float,
            ],
        ) -> None:
            assert (
                dataset_manifest
                is manifest
            )

            captured.metadata_root = (
                metadata_root
            )

            captured.patients_root = (
                patients_root
            )

            captured.calibration_config = (
                calibration_config
            )

            captured.git_commit_sha = (
                git_commit_sha
            )

            captured.git_dirty = (
                git_dirty
            )

            captured.target_spacing = (
                target_spacing
            )

        def freeze_patient(
            self,
            *,
            patient_id: int,
            cache_dir: Path,
            output_dir: Path,
            workers: int = 1,
        ) -> FrozenV2PredictionArtifact:
            captured.patient_id = (
                patient_id
            )

            captured.cache_dir = (
                cache_dir
            )

            captured.output_dir = (
                output_dir
            )

            captured.workers = workers

            return make_artifact(
                output_dir
            )

    monkeypatch.setattr(
        single_patient_module,
        "load_cohort_experiment_config",
        fake_load_experiment,
    )

    monkeypatch.setattr(
        single_patient_module,
        "load_cfb_dataset_manifest",
        fake_load_manifest,
    )

    monkeypatch.setattr(
        single_patient_module,
        "read_repository_state",
        fake_repository_state,
    )

    monkeypatch.setattr(
        single_patient_module,
        "PatientTwinService",
        FakePatientTwinService,
    )

    result = freeze_patient_from_configs(
        patient_id=42,
        experiment_config_path=(
            tmp_path
            / "experiment.yaml"
        ),
        dataset_manifest_path=(
            tmp_path
            / "dataset.yaml"
        ),
        repo_root=tmp_path,
        cache_dir=(
            tmp_path
            / "cache"
        ),
        output_dir=(
            tmp_path
            / "artifact"
        ),
        workers=3,
    )

    assert (
        result.directory
        == tmp_path / "artifact"
    )

    assert (
        captured.metadata_root
        == experiment.metadata_root
    )

    assert (
        captured.patients_root
        == experiment.patients_root
    )

    assert (
        captured.git_commit_sha
        == GIT_SHA
    )

    assert captured.git_dirty is False

    assert (
        captured.target_spacing
        == (
            2.0,
            2.0,
            2.0,
        )
    )

    assert captured.patient_id == 42

    assert (
        captured.cache_dir
        == tmp_path / "cache"
    )

    assert (
        captured.output_dir
        == tmp_path / "artifact"
    )

    assert captured.workers == 3

    config = (
        captured.calibration_config
    )

    assert config is not None
    assert config.dt_days == 2.0


def test_freeze_rejects_patient_outside_experiment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    experiment = make_experiment(
        tmp_path
    )

    def fake_load_experiment(
        path: Path,
    ) -> CohortExperimentConfig:
        return experiment

    monkeypatch.setattr(
        single_patient_module,
        "load_cohort_experiment_config",
        fake_load_experiment,
    )

    with pytest.raises(
        ValueError,
        match=(
            "not selected by "
            "the experiment config"
        ),
    ):
        freeze_patient_from_configs(
            patient_id=999,
            experiment_config_path=(
                tmp_path
                / "experiment.yaml"
            ),
            dataset_manifest_path=(
                tmp_path
                / "dataset.yaml"
            ),
            repo_root=tmp_path,
            cache_dir=(
                tmp_path
                / "cache"
            ),
            output_dir=(
                tmp_path
                / "artifact"
            ),
        )