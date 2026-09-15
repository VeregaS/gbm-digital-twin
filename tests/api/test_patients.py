from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import gbm_twin.api.routes.patients as patients_routes
from gbm_twin.api.app import create_app
from gbm_twin.api.config import (
    ApiSettings,
)
from gbm_twin.workflows.patient_catalog import (
    PatientCatalogSummary,
    PatientCatalogTimepoint,
    PatientTreatmentSummary,
)


def make_settings(
    tmp_path: Path,
) -> ApiSettings:
    return ApiSettings(
        dataset_root=tmp_path,
        metadata_root=(
            tmp_path / "metadata"
        ),
        patients_root=(
            tmp_path / "patients"
        ),
    )


def make_summary() -> PatientCatalogSummary:
    return PatientCatalogSummary(
        patient_id=108,
        timepoints=(
            PatientCatalogTimepoint(
                name="t0",
                days_from_baseline=0.0,
                gtv_available=True,
                gtv_type="manual",
                rtdose_available=False,
            ),
            PatientCatalogTimepoint(
                name="t1",
                days_from_baseline=98.0,
                gtv_available=True,
                gtv_type="manual",
                rtdose_available=False,
            ),
            PatientCatalogTimepoint(
                name="t2",
                days_from_baseline=252.0,
                gtv_available=True,
                gtv_type="manual",
                rtdose_available=False,
            ),
        ),
        dt01_days=98.0,
        dt12_days=154.0,
        treatment=(
            PatientTreatmentSummary(
                has_record=True,
                rt_start_day=14.0,
                rt_start_phase=(
                    "between_t0_t1"
                ),
                rt_started_by_t1=True,
                rt_started_by_t2=True,
                dose_gy=60.0,
                fractions=30,
                reconstructable=True,
            )
        ),
    )


def test_list_patients(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        patients_routes,
        "discover_patient_ids",
        lambda patients_root: (
            8,
            42,
            108,
        ),
    )

    client = TestClient(
        create_app(
            make_settings(tmp_path)
        )
    )

    response = client.get(
        "/api/patients"
    )

    assert response.status_code == 200

    assert response.json() == {
        "patients": [
            {
                "patient_id": 8,
                "label": "Patient 8",
            },
            {
                "patient_id": 42,
                "label": "Patient 42",
            },
            {
                "patient_id": 108,
                "label": "Patient 108",
            },
        ]
    }


def test_get_patient(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        patients_routes,
        "discover_patient_ids",
        lambda patients_root: (
            108,
        ),
    )

    monkeypatch.setattr(
        patients_routes,
        "get_patient_catalog_summary",
        lambda **kwargs: make_summary(),
    )

    client = TestClient(
        create_app(
            make_settings(tmp_path)
        )
    )

    response = client.get(
        "/api/patients/108"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["patient_id"] == 108
    assert payload["timepoint_count"] == 3
    assert payload["dt01_days"] == 98.0
    assert payload["dt12_days"] == 154.0

    assert (
        payload["treatment"]["dose_gy"]
        == 60.0
    )

    assert (
        payload["treatment"][
            "reconstructable"
        ]
        is True
    )


def test_get_missing_patient(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        patients_routes,
        "discover_patient_ids",
        lambda patients_root: (
            8,
            42,
        ),
    )

    client = TestClient(
        create_app(
            make_settings(tmp_path)
        )
    )

    response = client.get(
        "/api/patients/108"
    )

    assert response.status_code == 404