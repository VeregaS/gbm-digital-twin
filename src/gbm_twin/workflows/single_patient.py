from __future__ import annotations

from pathlib import Path

from gbm_twin.data.dataset_manifest import (
    load_cfb_dataset_manifest,
)
from gbm_twin.evaluation.config import (
    CohortExperimentConfig,
    load_cohort_experiment_config,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
)
from gbm_twin.workflows.patient_twin import (
    PatientTwinService,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)
from gbm_twin.workflows.repository import (
    read_repository_state,
)


def calibration_config_from_experiment(
    experiment: CohortExperimentConfig,
) -> V2CalibrationConfig:
    evaluation = experiment.evaluation

    return V2CalibrationConfig(
        diffusion_values=(
            evaluation.diffusion_values
        ),
        proliferation_values=(
            evaluation.proliferation_values
        ),
        dt_days=evaluation.dt,
        observation_threshold=(
            evaluation.threshold
        ),
        volume_weight=(
            evaluation.volume_weight
        ),
    )


def freeze_patient_from_configs(
    *,
    patient_id: int,
    experiment_config_path: Path,
    dataset_manifest_path: Path,
    repo_root: Path,
    cache_dir: Path,
    output_dir: Path,
    workers: int = 1,
) -> FrozenV2PredictionArtifact:
    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    experiment = (
        load_cohort_experiment_config(
            experiment_config_path
        )
    )

    if (
        patient_id
        not in experiment.patient_ids
    ):
        raise ValueError(
            f"Patient {patient_id} is not "
            "selected by the experiment config"
        )

    dataset_manifest = (
        load_cfb_dataset_manifest(
            dataset_manifest_path
        )
    )

    repository_state = (
        read_repository_state(
            repo_root
        )
    )

    calibration_config = (
        calibration_config_from_experiment(
            experiment
        )
    )

    service = PatientTwinService(
        metadata_root=(
            experiment.metadata_root
        ),
        patients_root=(
            experiment.patients_root
        ),
        dataset_manifest=(
            dataset_manifest
        ),
        calibration_config=(
            calibration_config
        ),
        git_commit_sha=(
            repository_state.commit_sha
        ),
        git_dirty=(
            repository_state.dirty
        ),
        target_spacing=(
            experiment
            .evaluation
            .target_spacing
        ),
    )

    return service.freeze_patient(
        patient_id=patient_id,
        cache_dir=cache_dir,
        output_dir=output_dir,
        workers=workers,
    )