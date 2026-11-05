from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import gbm_twin.api.routes.twin as twin_routes
from gbm_twin.api.app import create_app
from gbm_twin.api.config import ApiSettings
from gbm_twin.workflows.twin_anatomy import (
    TwinAnatomicalChange,
    TwinAnatomicalImpactReport,
    TwinAnatomicalRegionImpact,
    TwinAtlasReviewEvidence,
)


def _settings(
    tmp_path: Path,
) -> ApiSettings:
    return ApiSettings(
        dataset_root=tmp_path,
        metadata_root=tmp_path / "metadata",
        patients_root=tmp_path / "patients",
        atlas_root=tmp_path / "atlas",
        cohort_freeze_root=tmp_path / "freeze",
        cohort_evaluation_root=tmp_path / "evaluation",
    )


def _report(
) -> TwinAnatomicalImpactReport:
    current = (
        TwinAnatomicalRegionImpact(
            severity="high",
            region_label=12,
            region_name="Left inferior frontal gyrus",
            category="language",
            laterality="left",
            functional_note="Language-associated cortex",
            mask_overlap_cm3=1.2,
            density_overlap_cm3=1.8,
            min_distance_mm=0.0,
        ),
    )

    forecast = (
        TwinAnatomicalRegionImpact(
            severity="moderate",
            region_label=33,
            region_name="Left precentral gyrus",
            category="motor",
            laterality="left",
            functional_note="Motor-associated cortex",
            mask_overlap_cm3=0.0,
            density_overlap_cm3=0.5,
            min_distance_mm=3.0,
        ),
    )

    return TwinAnatomicalImpactReport(
        patient_id=42,
        current_timepoint="t1",
        forecast_timepoint="t2",
        configured=True,
        atlas_name="Research atlas",
        status_message="ok",
        registration=(
            TwinAtlasReviewEvidence(
                timepoint_name="t1",
                verified=True,
                decision="accepted",
                automatic_qc_status="pass",
                reviewed_at_utc=(
                    "2026-09-30T00:00:00+00:00"
                ),
                status_message="verified",
            )
        ),
        current=current,
        forecast=forecast,
        changes=(
            TwinAnatomicalChange(
                status="new",
                region_label=33,
                region_name="Left precentral gyrus",
                category="motor",
                laterality="left",
                functional_note="Motor-associated cortex",
                current_severity=None,
                forecast_severity="moderate",
            ),
        ),
    )


def test_twin_anatomical_impact_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        twin_routes,
        "_load_evaluation",
        lambda settings: object(),
    )

    monkeypatch.setattr(
        twin_routes,
        "_find_patient",
        lambda evaluation, patient_id: {
            "patient_id": patient_id,
        },
    )

    monkeypatch.setattr(
        twin_routes,
        "analyze_twin_anatomical_impact",
        lambda **kwargs: _report(),
    )

    client = TestClient(
        create_app(
            _settings(
                tmp_path
            )
        )
    )

    response = client.get(
        "/api/twin/patients/42/anatomical-impact"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload[
        "registration"
    ][
        "verified"
    ]

    assert payload[
        "current"
    ][0][
        "category"
    ] == "language"

    assert payload[
        "forecast"
    ][0][
        "category"
    ] == "motor"

    assert payload[
        "changes"
    ][0][
        "status"
    ] == "new"



def test_twin_anatomy_prepare_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[
        str,
        object,
    ] = {}

    monkeypatch.setattr(
        twin_routes,
        "_load_evaluation",
        lambda settings: object(),
    )

    monkeypatch.setattr(
        twin_routes,
        "_find_patient",
        lambda evaluation, patient_id: {
            "patient_id": patient_id,
        },
    )

    monkeypatch.setattr(
        twin_routes,
        "_require_twin_roots",
        lambda settings: (
            tmp_path / "freeze",
            tmp_path / "evaluation",
        ),
    )

    def fake_prepare(
        **kwargs: object,
    ) -> None:
        captured.update(
            kwargs
        )

    monkeypatch.setattr(
        twin_routes,
        "prepare_twin_anatomical_preview",
        fake_prepare,
    )

    client = TestClient(
        create_app(
            _settings(
                tmp_path
            )
        )
    )

    response = client.post(
        "/api/twin/patients/42/"
        "anatomical-impact/prepare"
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "preparing",
    }

    assert captured[
        "patient_id"
    ] == 42
