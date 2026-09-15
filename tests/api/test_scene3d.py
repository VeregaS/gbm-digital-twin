from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import gbm_twin.api.routes.viewer as viewer_routes
from gbm_twin.api.app import create_app
from gbm_twin.api.config import (
    ApiSettings,
)
from gbm_twin.workflows.scene3d import (
    SurfaceMesh,
    Viewer3DScene,
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


def make_mesh(
    name: str,
) -> SurfaceMesh:
    return SurfaceMesh(
        name=name,
        vertices=np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=np.float32,
        ),
        triangles=np.asarray(
            [
                [0, 1, 2],
            ],
            dtype=np.uint32,
        ),
        bounds=(
            0.0,
            1.0,
            0.0,
            1.0,
            0.0,
            0.0,
        ),
    )


def test_scene_3d_endpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    scene = Viewer3DScene(
        patient_id=108,
        timepoint_name="t1",
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
        latent_width_mm=4.0,
        latent_outer_level=0.2,
        latent_core_level=0.8,
        brain=make_mesh(
            "brain"
        ),
        gtv=make_mesh(
            "gtv"
        ),
        latent_outer=make_mesh(
            "latent_outer"
        ),
        latent_core=make_mesh(
            "latent_core"
        ),
    )

    monkeypatch.setattr(
        viewer_routes,
        "get_viewer_3d_scene",
        lambda **kwargs: scene,
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
            "viewer/t1/scene3d"
        
    )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["patient_id"]
        == 108
    )

    assert (
        payload["timepoint_name"]
        == "t1"
    )

    assert (
        payload["latent_width_mm"]
        == 4.0
    )

    assert (
        payload["latent_outer_level"]
        == 0.2
    )

    assert (
        payload["latent_core_level"]
        == 0.8
    )

    assert (
        payload["brain"][
            "vertex_count"
        ]
        == 3
    )

    assert (
        payload["gtv"][
            "triangle_count"
        ]
        == 1
    )

    assert (
        payload["latent_outer"][
            "triangle_count"
        ]
        == 1
    )

    assert (
        payload["latent_core"][
            "triangle_count"
        ]
        == 1
    )