import json
from pathlib import Path
from typing import cast

from gbm_twin.workflows.cohort_analysis import (
    _analysis_kind,
    load_sealed_cohort_analysis,
)
from gbm_twin.workflows.cohort_evaluation import CohortEvaluationPayload
from gbm_twin.workflows.provenance import sha256_file


def test_analysis_kind_tracks_evaluation_model_version() -> None:
    v2 = cast(
        CohortEvaluationPayload,
        {"kind": "v2_cohort_evaluation"},
    )
    v3 = cast(
        CohortEvaluationPayload,
        {
            "kind": "v3_cohort_evaluation",
            "model_version": "V3",
        },
    )

    assert _analysis_kind(v2) == (
        "v2_cohort_error_analysis",
        "V2",
    )
    assert _analysis_kind(v3) == (
        "v3_cohort_error_analysis",
        "V3",
    )


def test_load_sealed_v3_cohort_analysis(
    tmp_path: Path,
) -> None:
    root = tmp_path / "analysis"
    root.mkdir()
    payload = {
        "schema_version": 1,
        "kind": "v3_cohort_error_analysis",
        "model_version": "V3",
        "sealed": True,
        "summary": {},
        "patients": [],
    }
    manifest = root / "cohort_analysis.json"
    manifest.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (
        root / "cohort_analysis.sha256"
    ).write_text(
        sha256_file(manifest)
        + "  cohort_analysis.json\n",
        encoding="ascii",
    )

    loaded = load_sealed_cohort_analysis(root)
    assert loaded.manifest["kind"] == "v3_cohort_error_analysis"
    assert loaded.manifest["model_version"] == "V3"
