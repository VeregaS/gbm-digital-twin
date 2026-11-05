from __future__ import annotations

import json
from pathlib import Path

import pytest

from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_selection_artifact import (
    STAGE8_SELECTION_DESIGN,
    load_selected_stage8_model,
)


def _write_selection(root: Path, *, design: str = STAGE8_SELECTION_DESIGN) -> None:
    root.mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "kind": "stage8_development_model_selection",
        "sealed": True,
        "repository": {
            "commit_sha": "a" * 40,
            "dirty": False,
        },
        "source": {
            "stage8_data_audit_sha256": "b" * 64,
            "protocol_config_sha256": "c" * 64,
            "experiment_config_sha256": "d" * 64,
        },
        "leakage_control": {
            "internal_validation_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "candidate_selection_uses_only_development_exposed": True,
        },
        "selection_rule": {
            "design": design,
        },
        "selected_candidate": {
            "candidate_id": "stage8-spatial-alpha-0.12-prolif-sf-0.99",
            "use_spatial_rtdose": True,
            "effective_alpha_per_gy": 0.12,
            "alpha_beta_ratio_gy": 10.0,
            "proliferation_survival": 0.99,
            "use_infiltrative_observation": False,
        },
    }
    manifest_path = root / "stage8_model_selection.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "stage8_model_selection.sha256").write_text(
        sha256_file(manifest_path) + "  stage8_model_selection.json\n",
        encoding="ascii",
    )


def test_load_selected_stage8_model_accepts_nested_selection(
    tmp_path: Path,
) -> None:
    root = tmp_path / "selection"
    _write_selection(root)

    selected = load_selected_stage8_model(root)

    assert selected.selection_design == STAGE8_SELECTION_DESIGN
    assert selected.candidate.use_spatial_rtdose is True
    assert selected.candidate.effective_alpha_per_gy == pytest.approx(0.12)
    assert selected.candidate.proliferation_survival == pytest.approx(0.99)


def test_load_selected_stage8_model_rejects_old_selection_design(
    tmp_path: Path,
) -> None:
    root = tmp_path / "selection"
    _write_selection(root, design="cartesian_v0")

    with pytest.raises(ValueError, match="Unsupported Stage 8 model-selection design"):
        load_selected_stage8_model(root)
