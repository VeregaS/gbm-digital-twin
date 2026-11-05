from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import gbm_twin.api.routes.twin as twin_routes
from gbm_twin.api.app import create_app
from gbm_twin.api.config import ApiSettings
from gbm_twin.workflows.twin_reliability import (
    ForecastReliabilityFactor,
    TwinForecastReliability,
)


def _settings(
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


def test_twin_reliability_endpoint(
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
        "get_twin_forecast_reliability",
        lambda **kwargs: (
            TwinForecastReliability(
                patient_id=42,
                status="limited",
                model_version="V2",
                protocol_version=(
                    "v2-frozen-1"
                ),
                sealed=True,
                source_git_commit_sha=(
                    "a" * 40
                ),
                source_git_dirty=False,
                forecast_horizon_days=90.0,
                calibration_identifiable=False,
                diffusion_at_boundary=True,
                proliferation_at_boundary=False,
                prediction_empty=False,
                prediction_component_count=1,
                prediction_largest_component_fraction=1.0,
                prediction_outside_brain_fraction=0.0,
                factors=(
                    ForecastReliabilityFactor(
                        code=(
                            "calibration_non_identifiable"
                        ),
                        level="limited",
                        message="not identifiable",
                    ),
                ),
            )
        ),
    )

    client = TestClient(
        create_app(
            _settings(
                tmp_path
            )
        )
    )

    response = client.get(
        "/api/twin/patients/42/reliability"
    )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload[
            "status"
        ]
        == "limited"
    )

    assert (
        payload[
            "model_version"
        ]
        == "V2"
    )

    assert (
        payload[
            "factors"
        ][0][
            "code"
        ]
        == "calibration_non_identifiable"
    )
