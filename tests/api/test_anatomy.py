from pathlib import Path

import pytest
from fastapi.testclient import (
    TestClient,
)

import gbm_twin.api.routes.anatomy as anatomy_routes
from gbm_twin.anatomy.models import (
    AnatomicalRiskReport,
    AnatomicalWarning,
)
from gbm_twin.api.app import (
    create_app,
)
from gbm_twin.api.config import (
    ApiSettings,
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
        atlas_root=(
            tmp_path
            / "atlas"
        ),
    )


def make_report(
) -> AnatomicalRiskReport:
    return AnatomicalRiskReport(
        patient_id=108,
        timepoint_name="t1",
        configured=True,
        atlas_name=(
            "Research atlas"
        ),
        status_message="ok",
        latent_level=0.2,
        proximity_threshold_mm=5.0,
        warnings=(
            AnatomicalWarning(
                severity="high",
                region_label=12,
                region_name=(
                    "Left precentral region"
                ),
                category="motor",
                laterality="left",
                functional_note=(
                    "Motor-associated cortex"
                ),
                observed_overlap_cm3=1.2,
                latent_overlap_cm3=2.1,
                min_observed_distance_mm=0.0,
                message=(
                    "Observed GTV intersects "
                    "atlas-defined region."
                ),
            ),
        ),
    )


def test_anatomy_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        anatomy_routes,
        "analyze_patient_anatomy",
        lambda **kwargs: (
            make_report()
        ),
    )

    client = TestClient(
        create_app(
            make_settings(
                tmp_path
            )
        )
    )

    response = client.get(
        "/api/patients/108/"
        "anatomy/t1"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload[
        "configured"
    ]

    assert (
        payload[
            "high_count"
        ]
        == 1
    )

    assert (
        payload[
            "warnings"
        ][0][
            "category"
        ]
        == "motor"
    )
