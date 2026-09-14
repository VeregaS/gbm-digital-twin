from fastapi.testclient import TestClient

from gbm_twin.api.app import create_app


def test_health_endpoint() -> None:
    client = TestClient(
        create_app()
    )

    response = client.get(
        "/api/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok",
        "service": (
            "gbm-digital-twin-workbench"
        ),
        "version": "0.1.0",
    }