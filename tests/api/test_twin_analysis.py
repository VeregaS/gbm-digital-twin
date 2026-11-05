from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from gbm_twin.api.app import create_app
from gbm_twin.api.config import ApiSettings


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _analysis_payload(
    source_evaluation_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "kind": "v2_cohort_error_analysis",
        "sealed": True,
        "source_evaluation_sha256": source_evaluation_sha256,
        "source_freeze_manifest_sha256": "a" * 64,
        "analysis_config_sha256": "b" * 64,
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": "10.7937/v9pn-2f72",
        },
        "repository": {
            "commit_sha": "0123456789abcdef",
            "dirty": False,
        },
        "analysis_config": {
            "stable_volume_change_fraction": 0.1,
            "worst_patient_count": 5,
            "min_correlation_patients": 3,
        },
        "summary": {
            "patient_count": 1,
            "mean_twin_dice": 0.8,
            "median_twin_dice": 0.8,
            "mean_delta_vs_persistence": 0.1,
            "median_delta_vs_persistence": 0.1,
            "mean_delta_vs_volume_baseline": 0.05,
            "median_delta_vs_volume_baseline": 0.05,
            "twin_better_than_persistence_count": 1,
            "twin_equal_to_persistence_count": 0,
            "twin_worse_than_persistence_count": 0,
            "twin_better_than_volume_baseline_count": 1,
            "twin_equal_to_volume_baseline_count": 0,
            "twin_worse_than_volume_baseline_count": 0,
            "qc_flagged_count": 0,
            "calibration_non_identifiable_count": 0,
            "calibration_boundary_count": 0,
            "worst_twin_dice_patient_ids": [42],
            "worst_delta_vs_persistence_patient_ids": [42],
            "forecast_horizon_vs_twin_dice": {
                "count": 1,
                "pearson": None,
                "spearman": None,
            },
            "volume_change_t1_t2_vs_twin_dice": {
                "count": 1,
                "pearson": None,
                "spearman": None,
            },
            "calibration_dice_vs_twin_dice": {
                "count": 1,
                "pearson": None,
                "spearman": None,
            },
            "trajectory_groups": [
                {
                    "trajectory": "growth",
                    "patient_count": 1,
                    "mean_twin_dice": 0.8,
                    "mean_delta_vs_persistence": 0.1,
                    "mean_hd95_mm": 4.0,
                }
            ],
        },
        "patients": [
            {
                "patient_id": 42,
                "calibration_days": 60.0,
                "forecast_horizon_days": 90.0,
                "target_day": 150.0,
                "rt_start_day": 7.0,
                "rt_started_by_t1": True,
                "treatment_reconstructable": True,
                "volume_t0_cm3": 10.0,
                "volume_t1_cm3": 12.0,
                "volume_t2_cm3": 15.0,
                "volume_change_t0_t1": 0.2,
                "volume_change_t1_t2": 0.25,
                "trajectory_t0_t1": "growth",
                "trajectory_t1_t2": "growth",
                "diffusion": 0.015,
                "proliferation": 0.035,
                "calibration_dice": 0.9,
                "calibration_volume_error": 0.1,
                "calibration_loss": 0.2,
                "calibration_identifiable": True,
                "diffusion_at_boundary": False,
                "proliferation_at_boundary": False,
                "twin_dice": 0.8,
                "twin_volume_error": 0.1,
                "twin_hd95_mm": 4.0,
                "twin_centroid_distance_mm": 2.0,
                "persistence_dice": 0.7,
                "persistence_volume_error": 0.2,
                "volume_baseline_dice": 0.75,
                "volume_baseline_volume_error": 0.15,
                "twin_minus_persistence_dice": 0.1,
                "twin_minus_volume_baseline_dice": 0.05,
                "qc_warning_codes": [],
                "observed_outside_brain_fraction": 0.0,
                "twin_outside_brain_fraction": 0.0,
                "observed_component_count": 1,
                "twin_component_count": 1,
                "observed_largest_component_fraction": 1.0,
                "twin_largest_component_fraction": 1.0,
            }
        ],
    }


def _client(
    tmp_path: Path,
) -> tuple[TestClient, Path, Path]:
    evaluation_root = tmp_path / "evaluation"
    analysis_root = tmp_path / "analysis"

    evaluation_root.mkdir()
    analysis_root.mkdir()

    evaluation_path = (
        evaluation_root
        / "cohort_evaluation.json"
    )

    evaluation_path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    payload = _analysis_payload(
        _sha256(evaluation_path)
    )

    analysis_path = (
        analysis_root
        / "cohort_analysis.json"
    )

    analysis_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    (
        analysis_root
        / "cohort_analysis.sha256"
    ).write_text(
        _sha256(analysis_path)
        + "  cohort_analysis.json\n",
        encoding="ascii",
    )

    (
        analysis_root
        / "cohort_analysis.csv"
    ).write_text(
        "patient_id,twin_dice\n42,0.8\n",
        encoding="utf-8",
    )

    settings = ApiSettings(
        dataset_root=tmp_path,
        metadata_root=tmp_path,
        patients_root=tmp_path,
        cohort_evaluation_root=(
            evaluation_root
        ),
        cohort_analysis_root=(
            analysis_root
        ),
    )

    return (
        TestClient(
            create_app(settings)
        ),
        evaluation_path,
        analysis_root,
    )


def test_get_twin_cohort_analysis(
    tmp_path: Path,
) -> None:
    client, _, _ = _client(
        tmp_path
    )

    response = client.get(
        "/api/twin/analysis"
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["summary"]["patient_count"] == 1
    assert payload["patients"][0]["patient_id"] == 42
    assert payload["patients"][0]["twin_dice"] == 0.8


def test_twin_cohort_analysis_rejects_stale_evaluation(
    tmp_path: Path,
) -> None:
    client, evaluation_path, _ = _client(
        tmp_path
    )

    evaluation_path.write_text(
        '{"changed": true}\n',
        encoding="utf-8",
    )

    response = client.get(
        "/api/twin/analysis"
    )

    assert response.status_code == 503
    assert "stale" in response.json()["detail"]


def test_export_twin_cohort_analysis_csv(
    tmp_path: Path,
) -> None:
    client, _, _ = _client(
        tmp_path
    )

    response = client.get(
        "/api/twin/analysis/export.csv"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "text/csv"
    )
    assert "patient_id,twin_dice" in response.text
