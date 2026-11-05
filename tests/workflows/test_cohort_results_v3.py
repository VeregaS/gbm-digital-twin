import json
from pathlib import Path

from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
    summarize_cohort_evaluation,
)
from gbm_twin.workflows.provenance import sha256_file


def test_load_sealed_v3_cohort_evaluation(
    tmp_path: Path,
) -> None:
    payload = {
        "schema_version": 1,
        "kind": "v3_cohort_evaluation",
        "model_version": "V3",
        "sealed": True,
        "source_freeze_manifest_sha256": "a" * 64,
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": "10.7937/v9pn-2f72",
        },
        "repository": {
            "commit_sha": "b" * 40,
            "dirty": False,
        },
        "target_spacing": [2.0, 2.0, 2.0],
        "source_artifacts": [
            {
                "patient_id": 42,
                "artifact_dir": "patients/patient-42/frozen-v3",
                "manifest_sha256": "c" * 64,
            }
        ],
        "patients": [
            {
                "patient_id": 42,
                "target_timepoint": "t2",
                "target_day": 120.0,
                "twin": {
                    "dice": 0.7,
                    "relative_volume_error": 0.1,
                    "hd95_mm": 5.0,
                    "centroid_distance_mm": 2.0,
                },
                "persistence": {
                    "dice": 0.6,
                    "relative_volume_error": 0.2,
                    "hd95_mm": 6.0,
                    "centroid_distance_mm": 3.0,
                },
                "volume_baseline": {
                    "dice": 0.65,
                    "relative_volume_error": 0.15,
                    "hd95_mm": 5.5,
                    "centroid_distance_mm": 2.5,
                },
            }
        ],
    }

    root = tmp_path / "evaluation"
    root.mkdir()
    manifest = root / "cohort_evaluation.json"
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (
        root / "cohort_evaluation.sha256"
    ).write_text(
        sha256_file(manifest)
        + "  cohort_evaluation.json\n",
        encoding="ascii",
    )

    loaded = load_sealed_cohort_evaluation(root)
    assert loaded.manifest["kind"] == "v3_cohort_evaluation"
    assert loaded.manifest["model_version"] == "V3"

    summary = summarize_cohort_evaluation(loaded.manifest)
    assert summary.patient_count == 1
    assert summary.twin.mean_dice == 0.7
    assert summary.twin_better_than_persistence_count == 1
