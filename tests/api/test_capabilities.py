from pathlib import Path

from fastapi.testclient import TestClient

from gbm_twin.api.app import create_app
from gbm_twin.api.config import (
    ApiSettings,
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
        atlas_root=(
            tmp_path / "atlas"
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


def test_capabilities_require_dataset(
    tmp_path: Path,
) -> None:
    atlas_root = (
        tmp_path / "atlas"
    )

    atlas_root.mkdir()

    for filename in (
        "manifest.json",
        "template_t1.nii.gz",
        "template_labels.nii.gz",
    ):
        (
            atlas_root / filename
        ).touch()

    client = TestClient(
        create_app(
            make_settings(tmp_path)
        )
    )

    response = client.get(
        "/api/capabilities"
    )

    assert response.status_code == 200

    payload = response.json()

    assert not payload[
        "patients"
    ]["available"]

    assert not payload[
        "viewer"
    ]["available"]

    assert not payload[
        "anatomy"
    ]["available"]

    assert payload[
        "anatomy"
    ]["reason"] == (
        "CFB-GBM dataset is not configured."
    )


def test_capabilities_report_available_features(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    settings.metadata_root.mkdir()
    settings.patients_root.mkdir()

    assert settings.atlas_root is not None

    settings.atlas_root.mkdir()

    for filename in (
        "manifest.json",
        "template_t1.nii.gz",
        "template_labels.nii.gz",
    ):
        (
            settings.atlas_root
            / filename
        ).touch()
        
        assert (
        settings.cohort_freeze_root
        is not None
    )

    assert (
        settings.cohort_evaluation_root
        is not None
    )

    settings.cohort_freeze_root.mkdir()

    settings.cohort_evaluation_root.mkdir()

    (
        settings.cohort_evaluation_root
        / "cohort_evaluation.json"
    ).touch()

    (
        settings.cohort_evaluation_root
        / "cohort_evaluation.sha256"
    ).touch()

    client = TestClient(
        create_app(settings)
    )

    response = client.get(
        "/api/capabilities"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload[
        "patients"
    ] == {
        "available": True,
        "reason": None,
    }

    assert payload[
        "viewer"
    ] == {
        "available": True,
        "reason": None,
    }

    assert payload[
        "anatomy"
    ] == {
        "available": True,
        "reason": None,
    }

    assert payload[
        "digital_twin"
    ] == {
        "available": True,
        "reason": None,
    }

    for feature in (
        "runs",
        "tools",
        "research",
    ):
        assert not payload[
            feature
        ]["available"]

        assert payload[
            feature
        ]["reason"]


def test_capabilities_require_atlas(
    tmp_path: Path,
) -> None:
    settings = make_settings(
        tmp_path
    )

    settings.metadata_root.mkdir()
    settings.patients_root.mkdir()

    client = TestClient(
        create_app(settings)
    )

    response = client.get(
        "/api/capabilities"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload[
        "patients"
    ]["available"]

    assert payload[
        "viewer"
    ]["available"]

    assert not payload[
        "anatomy"
    ]["available"]

    assert payload[
        "anatomy"
    ]["reason"] == (
        "Anatomical atlas is not configured."
    )
