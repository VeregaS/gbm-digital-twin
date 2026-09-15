from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import gbm_twin.api.routes.viewer as viewer_routes
from gbm_twin.api.app import create_app
from gbm_twin.api.config import (
    ApiSettings,
)
from gbm_twin.workflows.viewer import (
    ViewerPlaneMetadata,
    ViewerVolumeMetadata,
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


def make_metadata(
) -> ViewerVolumeMetadata:
    return ViewerVolumeMetadata(
        patient_id=108,
        timepoint_name="t1",
        shape=(
            130,
            130,
            105,
        ),
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
        intensity_low=10.0,
        intensity_high=900.0,
        gtv_voxels=1000,
        gtv_volume_cm3=8.0,
        planes=(
            ViewerPlaneMetadata(
                name="axial",
                size=105,
                max_index=104,
                default_index=52,
                image_width=130,
                image_height=130,
            ),
            ViewerPlaneMetadata(
                name="coronal",
                size=130,
                max_index=129,
                default_index=65,
                image_width=130,
                image_height=105,
            ),
            ViewerPlaneMetadata(
                name="sagittal",
                size=130,
                max_index=129,
                default_index=65,
                image_width=130,
                image_height=105,
            ),
        ),
    )


def test_viewer_metadata_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        viewer_routes,
        "get_viewer_volume_metadata",
        lambda **kwargs: (
            make_metadata()
        ),
    )

    client = TestClient(
        create_app(
            make_settings(tmp_path)
        )
    )

    response = client.get(
        "/api/patients/108/viewer/t1"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["patient_id"] == 108
    assert payload["timepoint_name"] == "t1"

    assert payload["shape"] == [
        130,
        130,
        105,
    ]

    assert (
        payload["planes"][0]["name"]
        == "axial"
    )

    assert (
        payload["planes"][0][
            "default_index"
        ]
        == 52
    )


def test_viewer_slice_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    png = (
        b"\x89PNG\r\n\x1a\n"
        b"test"
    )

    monkeypatch.setattr(
        viewer_routes,
        "render_viewer_slice_png",
        lambda **kwargs: png,
    )

    client = TestClient(
        create_app(
            make_settings(tmp_path)
        )
    )

    response = client.get(
        
            "/api/patients/108/"
            "viewer/t1/slice"
            "?plane=axial"
            "&index=52"
            "&overlay_gtv=true"
        
    )

    assert response.status_code == 200

    assert (
        response.headers[
            "content-type"
        ]
        == "image/png"
    )

    assert response.content == png