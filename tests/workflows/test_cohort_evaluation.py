from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.cohort_evaluation as cohort_module
from gbm_twin.data.nifti import (
    NiftiVolume,
)
from gbm_twin.evaluation.cohort import (
    EvaluationConfig,
)
from gbm_twin.evaluation.config import (
    CohortExperimentConfig,
)
from gbm_twin.evaluation.frozen_prediction import (
    FrozenV2EvaluationResult,
)
from gbm_twin.workflows.cohort_evaluation import (
    evaluate_frozen_cohort,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)

GIT_SHA = (
    "0123456789abcdef"
    "0123456789abcdef"
    "01234567"
)


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


def write_freeze_manifest(
    cohort_dir: Path,
) -> None:
    cohort_dir.mkdir(
        parents=True
    )

    payload = {
        "schema_version": 1,
        "kind": "v2_cohort_freeze",
        "frozen": True,
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": (
                "10.7937/v9pn-2f72"
            ),
        },
        "repository": {
            "commit_sha": GIT_SHA,
            "dirty": False,
        },
        "experiment": {
            "experiment_config_file": (
                "mini_cohort.yaml"
            ),
            "dataset_manifest_file": (
                "cfb_gbm_v4.yaml"
            ),
            "calibration_config_sha256": (
                "a" * 64
            ),
            "target_spacing": [
                2.0,
                2.0,
                2.0,
            ],
            "selected_patient_ids": [
                42,
                108,
            ],
        },
        "frozen_patients": [
            {
                "patient_id": 42,
                "artifact_dir": (
                    "patients/"
                    "patient-42/"
                    "frozen-v2"
                ),
            },
            {
                "patient_id": 108,
                "artifact_dir": (
                    "patients/"
                    "patient-108/"
                    "frozen-v2"
                ),
            },
        ],
        "excluded_patients": [],
    }

    manifest_path = (
        cohort_dir
        / "cohort_manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (
        cohort_dir
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


def write_patient_manifest(
    artifact_dir: Path,
    patient_id: int,
) -> None:
    artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        artifact_dir
        / "manifest.json"
    )

    path.write_text(
        json.dumps(
            {
                "patient_id": (
                    patient_id
                ),
            }
        ),
        encoding="utf-8",
    )


def make_artifact(
    artifact_dir: Path,
    patient_id: int,
) -> FrozenV2PredictionArtifact:
    mask = np.zeros(
        (3, 3, 3),
        dtype=bool,
    )

    return FrozenV2PredictionArtifact(
        directory=artifact_dir,
        manifest={
            "patient_id": (
                patient_id
            ),
        },
        prediction_field=(
            mask.astype(
                np.float32
            )
        ),
        prediction_mask=mask,
        persistence_mask=(
            mask.copy()
        ),
        volume_baseline_mask=(
            mask.copy()
        ),
    )


def make_target(
    patient_id: int,
) -> PreparedPatientTimepoint:
    data = np.zeros(
        (3, 3, 3),
        dtype=np.float32,
    )

    data[
        1,
        1,
        1,
    ] = 1.0

    volume = NiftiVolume(
        path=Path(
            f"{patient_id}_t2.nii.gz"
        ),
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

    return PreparedPatientTimepoint(
        patient_id=patient_id,
        name="t2",
        days_from_baseline=120.0,
        t1gd=volume,
        gtv=volume,
        brain_mask=volume,
    )


def make_evaluation(
    patient_id: int,
) -> FrozenV2EvaluationResult:
    return FrozenV2EvaluationResult(
        patient_id=patient_id,
        target_timepoint="t2",
        target_day=120.0,
        prediction_dice=0.7,
        prediction_volume_error=0.1,
        prediction_hd95_mm=4.0,
        prediction_centroid_distance_mm=2.0,
        persistence_dice=0.6,
        persistence_volume_error=0.2,
        persistence_hd95_mm=6.0,
        persistence_centroid_distance_mm=3.0,
        volume_baseline_dice=0.5,
        volume_baseline_volume_error=0.05,
        volume_baseline_hd95_mm=8.0,
        volume_baseline_centroid_distance_mm=4.0,
    )


def test_reveal_validates_all_artifacts_before_loading_t2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cohort_dir = (
        tmp_path
        / "freeze"
    )

    write_freeze_manifest(
        cohort_dir
    )

    artifact_dirs = {
        42: (
            cohort_dir
            / "patients"
            / "patient-42"
            / "frozen-v2"
        ),
        108: (
            cohort_dir
            / "patients"
            / "patient-108"
            / "frozen-v2"
        ),
    }

    for (
        patient_id,
        artifact_dir,
    ) in artifact_dirs.items():
        write_patient_manifest(
            artifact_dir,
            patient_id,
        )

    events: list[str] = []

    def fake_load_artifact(
        artifact_dir: Path,
    ) -> FrozenV2PredictionArtifact:
        patient_id = (
            42
            if "patient-42"
            in artifact_dir.parts
            else 108
        )

        events.append(
            f"validate:{patient_id}"
        )

        return make_artifact(
            artifact_dir,
            patient_id,
        )

    def fake_load_experiment(
        path: Path,
    ) -> CohortExperimentConfig:
        return make_experiment(
            tmp_path
        )

    def fake_prepare(
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
        assert timepoint_name == "t2"

        events.append(
            f"prepare:{patient_id}"
        )

        return make_target(
            patient_id
        )

    def fake_evaluate(
        *,
        artifact_dir: Path,
        observed_target: (
            PreparedPatientTimepoint
        ),
    ) -> FrozenV2EvaluationResult:
        events.append(
            "evaluate:"
            f"{observed_target.patient_id}"
        )

        return make_evaluation(
            observed_target.patient_id
        )

    monkeypatch.setattr(
        cohort_module,
        "load_frozen_v2_prediction",
        fake_load_artifact,
    )

    monkeypatch.setattr(
        cohort_module,
        "load_cohort_experiment_config",
        fake_load_experiment,
    )

    monkeypatch.setattr(
        cohort_module,
        "prepare_patient_timepoint",
        fake_prepare,
    )

    monkeypatch.setattr(
        cohort_module,
        "evaluate_frozen_v2_prediction",
        fake_evaluate,
    )

    result = evaluate_frozen_cohort(
        cohort_dir=cohort_dir,
        experiment_config_path=(
            tmp_path
            / "mini_cohort.yaml"
        ),
        output_dir=(
            tmp_path
            / "evaluation"
        ),
    )

    assert events[:2] == [
        "validate:42",
        "validate:108",
    ]

    assert events[2:] == [
        "prepare:42",
        "evaluate:42",
        "prepare:108",
        "evaluate:108",
    ]

    assert (
        result.evaluated_patient_ids
        == (
            42,
            108,
        )
    )

    assert (
        result.directory
        / "cohort_evaluation.json"
    ).is_file()

    assert (
        result.directory
        / "cohort_evaluation.sha256"
    ).is_file()

    first = (
        result.manifest[
            "patients"
        ][0]
    )

    assert (
        first["twin"]["dice"]
        == 0.7
    )

    assert (
        first[
            "twin"
        ][
            "hd95_mm"
        ]
        == 4.0
    )


def test_modified_freeze_manifest_is_rejected_before_t2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cohort_dir = (
        tmp_path
        / "freeze"
    )

    write_freeze_manifest(
        cohort_dir
    )

    manifest_path = (
        cohort_dir
        / "cohort_manifest.json"
    )

    manifest_path.write_text(
        (
            manifest_path.read_text(
                encoding="utf-8"
            )
            + " "
        ),
        encoding="utf-8",
    )

    def fail_prepare(
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
        pytest.fail(
            "t2 must not be loaded "
            "for an invalid cohort seal"
        )

    monkeypatch.setattr(
        cohort_module,
        "prepare_patient_timepoint",
        fail_prepare,
    )

    with pytest.raises(
        ValueError,
        match="checksum mismatch",
    ):
        evaluate_frozen_cohort(
            cohort_dir=cohort_dir,
            experiment_config_path=(
                tmp_path
                / "mini_cohort.yaml"
            ),
            output_dir=(
                tmp_path
                / "evaluation"
            ),
        )


def test_reveal_rejects_artifact_path_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cohort_dir = (
        tmp_path
        / "freeze"
    )

    cohort_dir.mkdir(
        parents=True
    )

    payload = {
        "schema_version": 1,
        "kind": "v2_cohort_freeze",
        "frozen": True,
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": (
                "10.7937/v9pn-2f72"
            ),
        },
        "repository": {
            "commit_sha": GIT_SHA,
            "dirty": False,
        },
        "experiment": {
            "experiment_config_file": (
                "mini_cohort.yaml"
            ),
            "target_spacing": [
                2.0,
                2.0,
                2.0,
            ],
        },
        "frozen_patients": [
            {
                "patient_id": 42,
                "artifact_dir": (
                    "../../outside"
                ),
            },
        ],
    }

    path = (
        cohort_dir
        / "cohort_manifest.json"
    )

    path.write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )

    (
        cohort_dir
        / "cohort_manifest.sha256"
    ).write_text(
        (
            sha256_file(
                path
            )
            + "  cohort_manifest.json\n"
        ),
        encoding="ascii",
    )
    
    def fake_load_experiment(
        path: Path,
    ) -> CohortExperimentConfig:
        return make_experiment(
            tmp_path
        )

    monkeypatch.setattr(
        cohort_module,
        "load_cohort_experiment_config",
        fake_load_experiment,
    )

    with pytest.raises(
        ValueError,
        match="must not escape",
    ):
        evaluate_frozen_cohort(
            cohort_dir=cohort_dir,
            experiment_config_path=(
                tmp_path
                / "mini_cohort.yaml"
            ),
            output_dir=(
                tmp_path
                / "evaluation"
            ),
        )