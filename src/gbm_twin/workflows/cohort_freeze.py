from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from gbm_twin.data.dataset_manifest import (
    CFBDatasetManifest,
    load_cfb_dataset_manifest,
)
from gbm_twin.evaluation.config import (
    CohortExperimentConfig,
    load_cohort_experiment_config,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
)
from gbm_twin.workflows.eligibility import (
    PatientEligibility,
)
from gbm_twin.workflows.patient_twin import (
    PatientTwinService,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
    v2_calibration_config_sha256,
)
from gbm_twin.workflows.repository import (
    RepositoryState,
    read_repository_state,
)
from gbm_twin.workflows.single_patient import (
    calibration_config_from_experiment,
)

COHORT_FREEZE_SCHEMA_VERSION = 1


class EligibilityIssuePayload(TypedDict):
    reason: str
    detail: str


class FrozenPatientPayload(TypedDict):
    patient_id: int
    artifact_dir: str


class ExcludedPatientPayload(TypedDict):
    patient_id: int
    issues: list[EligibilityIssuePayload]


class DatasetPayload(TypedDict):
    name: str
    version: int
    doi: str


class RepositoryPayload(TypedDict):
    commit_sha: str
    dirty: bool


class ExperimentPayload(TypedDict):
    experiment_config_file: str
    dataset_manifest_file: str
    calibration_config_sha256: str
    target_spacing: list[float]
    selected_patient_ids: list[int]


class CohortFreezeManifestPayload(TypedDict):
    schema_version: int
    kind: str
    frozen: bool
    dataset: DatasetPayload
    repository: RepositoryPayload
    experiment: ExperimentPayload
    frozen_patients: list[FrozenPatientPayload]
    excluded_patients: list[ExcludedPatientPayload]


@dataclass(frozen=True)
class CohortFreezeResult:
    directory: Path
    manifest: CohortFreezeManifestPayload

    @property
    def frozen_patient_ids(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            patient["patient_id"]
            for patient
            in self.manifest[
                "frozen_patients"
            ]
        )

    @property
    def excluded_patient_ids(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            patient["patient_id"]
            for patient
            in self.manifest[
                "excluded_patients"
            ]
        )


def _eligibility_payload(
    eligibility: PatientEligibility,
) -> ExcludedPatientPayload:
    return {
        "patient_id": (
            eligibility.patient_id
        ),
        "issues": [
            {
                "reason": (
                    issue.reason.value
                ),
                "detail": issue.detail,
            }
            for issue
            in eligibility.issues
        ],
    }


def _build_service(
    *,
    experiment: CohortExperimentConfig,
    dataset_manifest: CFBDatasetManifest,
    calibration_config: V2CalibrationConfig,
    repository_state: RepositoryState,
) -> PatientTwinService:
    return PatientTwinService(
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


def freeze_cohort_from_configs(
    *,
    experiment_config_path: Path,
    dataset_manifest_path: Path,
    repo_root: Path,
    cache_root: Path,
    output_root: Path,
    workers: int = 1,
    allow_dirty: bool = False,
) -> CohortFreezeResult:
    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    destination = output_root.resolve()

    if destination.exists():
        raise FileExistsError(
            "Cohort freeze destination "
            f"already exists: {destination}"
        )

    experiment = (
        load_cohort_experiment_config(
            experiment_config_path
        )
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

    if (
        repository_state.dirty
        and not allow_dirty
    ):
        raise ValueError(
            "Cohort freeze requires a clean "
            "Git working tree"
        )

    calibration_config = (
        calibration_config_from_experiment(
            experiment
        )
    )

    service = _build_service(
        experiment=experiment,
        dataset_manifest=(
            dataset_manifest
        ),
        calibration_config=(
            calibration_config
        ),
        repository_state=(
            repository_state
        ),
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=(
                f".{destination.name}-"
            ),
        )
    )

    frozen_patients: list[
        FrozenPatientPayload
    ] = []

    excluded_patients: list[
        ExcludedPatientPayload
    ] = []

    try:
        for patient_id in (
            experiment.patient_ids
        ):
            eligibility = (
                service.assess_eligibility(
                    patient_id
                )
            )

            if not eligibility.eligible:
                excluded_patients.append(
                    _eligibility_payload(
                        eligibility
                    )
                )

                continue

            relative_artifact_dir = (
                Path("patients")
                / f"patient-{patient_id}"
                / "frozen-v2"
            )

            artifact_dir = (
                temporary
                / relative_artifact_dir
            )

            patient_cache_dir = (
                cache_root.resolve()
                / f"patient-{patient_id}"
            )

            service.freeze_patient(
                patient_id=patient_id,
                cache_dir=(
                    patient_cache_dir
                ),
                output_dir=artifact_dir,
                workers=workers,
            )

            frozen_patients.append(
                {
                    "patient_id": (
                        patient_id
                    ),
                    "artifact_dir": (
                        relative_artifact_dir
                        .as_posix()
                    ),
                }
            )

        manifest: (
            CohortFreezeManifestPayload
        ) = {
            "schema_version": (
                COHORT_FREEZE_SCHEMA_VERSION
            ),
            "kind": (
                "v2_cohort_freeze"
            ),
            "frozen": True,
            "dataset": {
                "name": (
                    dataset_manifest.name
                ),
                "version": (
                    dataset_manifest.version
                ),
                "doi": (
                    dataset_manifest.doi
                ),
            },
            "repository": {
                "commit_sha": (
                    repository_state
                    .commit_sha
                ),
                "dirty": (
                    repository_state.dirty
                ),
            },
            "experiment": {
                "experiment_config_file": (
                    experiment_config_path.name
                ),
                "dataset_manifest_file": (
                    dataset_manifest_path.name
                ),
                "calibration_config_sha256": (
                    v2_calibration_config_sha256(
                        calibration_config
                    )
                ),
                "target_spacing": list(
                    experiment
                    .evaluation
                    .target_spacing
                ),
                "selected_patient_ids": list(
                    experiment.patient_ids
                ),
            },
            "frozen_patients": (
                frozen_patients
            ),
            "excluded_patients": (
                excluded_patients
            ),
        }

        manifest_path = (
            temporary
            / "cohort_manifest.json"
        )

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            temporary
            / "cohort_manifest.sha256"
        ).write_text(
            (
                sha256_file(
                    manifest_path
                )
                + "  cohort_manifest.json\n"
            ),
            encoding="ascii",
        )

        temporary.rename(
            destination
        )

    except BaseException:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    return CohortFreezeResult(
        directory=destination,
        manifest=manifest,
    )