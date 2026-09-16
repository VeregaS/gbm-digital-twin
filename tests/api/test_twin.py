from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import (
    TestClient,
)

from gbm_twin.api.app import (
    create_app,
)
from gbm_twin.api.config import (
    ApiSettings,
)
from gbm_twin.api.schemas.twin import (
    TwinCohortResponse,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)

GIT_SHA = (
    "0123456789abcdef"
    "0123456789abcdef"
    "01234567"
)


def make_settings(
    tmp_path: Path,
) -> ApiSettings:
    return ApiSettings(
        dataset_root=tmp_path,
        metadata_root=(
            tmp_path
            / "metadata"
        ),
        patients_root=(
            tmp_path
            / "patients"
        ),
        cohort_freeze_root=(
            tmp_path
            / "freeze"
        ),
        cohort_evaluation_root=(
            tmp_path
            / "evaluation"
        ),
    )


def write_evaluation(
    root: Path,
) -> None:
    root.mkdir(
        parents=True
    )

    payload = {
        "schema_version": 1,
        "kind": (
            "v2_cohort_evaluation"
        ),
        "sealed": True,
        "source_freeze_manifest_sha256": (
            "a" * 64
        ),
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
        "target_spacing": [
            2.0,
            2.0,
            2.0,
        ],
        "source_artifacts": [
            {
                "patient_id": 42,
                "artifact_dir": (
                    "patients/"
                    "patient-42/"
                    "frozen-v2"
                ),
                "manifest_sha256": (
                    "b" * 64
                ),
            },
            {
                "patient_id": 108,
                "artifact_dir": (
                    "patients/"
                    "patient-108/"
                    "frozen-v2"
                ),
                "manifest_sha256": (
                    "c" * 64
                ),
            },
        ],
        "patients": [
            {
                "patient_id": 42,
                "target_timepoint": "t2",
                "target_day": 120.0,
                "twin": {
                    "dice": 0.8,
                    "relative_volume_error": 0.1,
                    "hd95_mm": 4.0,
                    "centroid_distance_mm": 2.0,
                },
                "persistence": {
                    "dice": 0.6,
                    "relative_volume_error": 0.2,
                    "hd95_mm": 8.0,
                    "centroid_distance_mm": 4.0,
                },
                "volume_baseline": {
                    "dice": 0.5,
                    "relative_volume_error": 0.05,
                    "hd95_mm": 10.0,
                    "centroid_distance_mm": 5.0,
                },
            },
            {
                "patient_id": 108,
                "target_timepoint": "t2",
                "target_day": 150.0,
                "twin": {
                    "dice": 0.4,
                    "relative_volume_error": 0.3,
                    "hd95_mm": 12.0,
                    "centroid_distance_mm": 6.0,
                },
                "persistence": {
                    "dice": 0.5,
                    "relative_volume_error": 0.2,
                    "hd95_mm": 10.0,
                    "centroid_distance_mm": 5.0,
                },
                "volume_baseline": {
                    "dice": 0.45,
                    "relative_volume_error": 0.1,
                    "hd95_mm": 11.0,
                    "centroid_distance_mm": 5.5,
                },
            },
        ],
    }

    manifest_path = (
        root
        / "cohort_evaluation.json"
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
        root
        / "cohort_evaluation.sha256"
    ).write_text(
        (
            sha256_file(
                manifest_path
            )
            + "  cohort_evaluation.json\n"
        ),
        encoding="ascii",
    )


def test_get_twin_cohort(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    evaluation_root = (
        settings
        .cohort_evaluation_root
    )

    assert evaluation_root is not None

    write_evaluation(
        evaluation_root
    )

    client = TestClient(
        create_app(
            settings
        )
    )

    response = client.get(
        "/api/twin/cohort"
    )

    assert response.status_code == 200

    payload = (
        TwinCohortResponse
        .model_validate(
            response.json()
        )
    )

    assert payload.schema_version == 1

    assert payload.dataset.name == (
        "CFB-GBM"
    )

    assert payload.dataset.version == 4

    assert payload.dataset.doi == (
        "10.7937/v9pn-2f72"
    )

    assert (
        payload.repository.commit_sha
        == GIT_SHA
    )

    assert not payload.repository.dirty

    assert payload.target_spacing == [
        2.0,
        2.0,
        2.0,
    ]

    assert payload.patient_count == 2

    assert (
        payload.twin.patient_count
        == 2
    )

    assert (
        payload.twin.hd95_count
        == 2
    )

    assert (
        payload.twin
        .centroid_distance_count
        == 2
    )

    assert (
        payload.twin.mean_dice
        == pytest.approx(
            0.6
        )
    )

    assert (
        payload.twin
        .mean_relative_volume_error
        == pytest.approx(
            0.2
        )
    )

    assert (
        payload.twin.mean_hd95_mm
        == pytest.approx(
            8.0
        )
    )

    assert (
        payload.twin
        .mean_centroid_distance_mm
        == pytest.approx(
            4.0
        )
    )

    assert (
        payload.persistence
        .mean_dice
        == pytest.approx(
            0.55
        )
    )

    assert (
        payload.persistence
        .mean_relative_volume_error
        == pytest.approx(
            0.2
        )
    )

    assert (
        payload.persistence
        .mean_hd95_mm
        == pytest.approx(
            9.0
        )
    )

    assert (
        payload.persistence
        .mean_centroid_distance_mm
        == pytest.approx(
            4.5
        )
    )

    assert (
        payload.volume_baseline
        .mean_dice
        == pytest.approx(
            0.475
        )
    )

    assert (
        payload.volume_baseline
        .mean_relative_volume_error
        == pytest.approx(
            0.075
        )
    )

    assert (
        payload.volume_baseline
        .mean_hd95_mm
        == pytest.approx(
            10.5
        )
    )

    assert (
        payload.volume_baseline
        .mean_centroid_distance_mm
        == pytest.approx(
            5.25
        )
    )

    assert (
        payload
        .twin_better_than_persistence_count
        == 1
    )

    assert (
        payload
        .twin_equal_to_persistence_count
        == 0
    )

    assert (
        payload
        .twin_worse_than_persistence_count
        == 1
    )


def test_list_twin_patients(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    evaluation_root = (
        settings
        .cohort_evaluation_root
    )

    assert evaluation_root is not None

    write_evaluation(
        evaluation_root
    )

    client = TestClient(
        create_app(
            settings
        )
    )

    response = client.get(
        "/api/twin/patients"
    )

    assert response.status_code == 200

    assert response.json() == {
        "patients": [
            {
                "patient_id": 42,
                "target_timepoint": "t2",
                "target_day": 120.0,
            },
            {
                "patient_id": 108,
                "target_timepoint": "t2",
                "target_day": 150.0,
            },
        ]
    }


def test_get_twin_patient(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    evaluation_root = (
        settings
        .cohort_evaluation_root
    )

    assert evaluation_root is not None

    write_evaluation(
        evaluation_root
    )

    client = TestClient(
        create_app(
            settings
        )
    )

    response = client.get(
        "/api/twin/patients/42"
    )

    assert response.status_code == 200

    assert response.json() == {
        "patient_id": 42,
        "target_timepoint": "t2",
        "target_day": 120.0,
        "twin": {
            "dice": 0.8,
            "relative_volume_error": 0.1,
            "hd95_mm": 4.0,
            "centroid_distance_mm": 2.0,
        },
        "persistence": {
            "dice": 0.6,
            "relative_volume_error": 0.2,
            "hd95_mm": 8.0,
            "centroid_distance_mm": 4.0,
        },
        "volume_baseline": {
            "dice": 0.5,
            "relative_volume_error": 0.05,
            "hd95_mm": 10.0,
            "centroid_distance_mm": 5.0,
        },
    }


def test_missing_twin_patient_returns_404(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    evaluation_root = (
        settings
        .cohort_evaluation_root
    )

    assert evaluation_root is not None

    write_evaluation(
        evaluation_root
    )

    client = TestClient(
        create_app(
            settings
        )
    )

    response = client.get(
        "/api/twin/patients/999"
    )

    assert response.status_code == 404


def test_tampered_evaluation_returns_503(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    evaluation_root = (
        settings
        .cohort_evaluation_root
    )

    assert evaluation_root is not None

    write_evaluation(
        evaluation_root
    )

    manifest_path = (
        evaluation_root
        / "cohort_evaluation.json"
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

    client = TestClient(
        create_app(
            settings
        )
    )

    response = client.get(
        "/api/twin/cohort"
    )

    assert response.status_code == 503

    assert (
        "checksum mismatch"
        in response.json()["detail"]
    )