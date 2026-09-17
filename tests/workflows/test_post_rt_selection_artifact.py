import json
from pathlib import Path

import pytest

from gbm_twin.workflows.post_rt_selection_artifact import (
    load_selected_post_rt_candidate,
)
from gbm_twin.workflows.provenance import sha256_file


def _write_selection(
    root: Path,
    experiment_config: Path,
    *,
    dirty: bool = False,
) -> None:
    root.mkdir(parents=True)

    payload = {
        "schema_version": 1,
        "kind": "v3_post_rt_parameter_selection",
        "sealed": True,
        "leakage_control": {
            "loads_t2_imaging": False,
            "selection_metric": "mean_t0_t1_calibration_loss",
            "uses_timepoints": ["t0", "t1"],
        },
        "repository": {
            "commit_sha": "a" * 40,
            "dirty": dirty,
        },
        "experiment": {
            "experiment_config_sha256": sha256_file(
                experiment_config
            ),
            "selection_config_sha256": "b" * 64,
        },
        "selected_candidate": {
            "candidate_id": "post-rt-k0.005-tau60",
            "initial_kill_rate_per_day": 0.005,
            "decay_time_days": 60.0,
        },
    }

    manifest = root / "post_rt_selection.json"
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (
        root / "post_rt_selection.sha256"
    ).write_text(
        sha256_file(manifest)
        + "  post_rt_selection.json\n",
        encoding="ascii",
    )


def test_load_selected_post_rt_candidate(
    tmp_path: Path,
) -> None:
    experiment = tmp_path / "experiment.yaml"
    experiment.write_text("patients: [42]\n", encoding="utf-8")
    selection_root = tmp_path / "selection"
    _write_selection(selection_root, experiment)

    selected = load_selected_post_rt_candidate(
        selection_root=selection_root,
        experiment_config_path=experiment,
    )

    assert selected.candidate_id == "post-rt-k0.005-tau60"
    assert selected.initial_kill_rate_per_day == pytest.approx(0.005)
    assert selected.decay_time_days == pytest.approx(60.0)
    assert selected.selection_config_sha256 == "b" * 64
    assert selected.source_manifest_sha256 == sha256_file(
        selection_root / "post_rt_selection.json"
    )


def test_selected_post_rt_candidate_rejects_tampering(
    tmp_path: Path,
) -> None:
    experiment = tmp_path / "experiment.yaml"
    experiment.write_text("patients: [42]\n", encoding="utf-8")
    selection_root = tmp_path / "selection"
    _write_selection(selection_root, experiment)

    manifest = selection_root / "post_rt_selection.json"
    manifest.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="checksum mismatch",
    ):
        load_selected_post_rt_candidate(
            selection_root=selection_root,
            experiment_config_path=experiment,
        )


def test_selected_post_rt_candidate_rejects_dirty_selection(
    tmp_path: Path,
) -> None:
    experiment = tmp_path / "experiment.yaml"
    experiment.write_text("patients: [42]\n", encoding="utf-8")
    selection_root = tmp_path / "selection"
    _write_selection(
        selection_root,
        experiment,
        dirty=True,
    )

    with pytest.raises(
        ValueError,
        match="clean Git working tree",
    ):
        load_selected_post_rt_candidate(
            selection_root=selection_root,
            experiment_config_path=experiment,
        )


def test_selected_post_rt_candidate_rejects_experiment_mismatch(
    tmp_path: Path,
) -> None:
    experiment = tmp_path / "experiment.yaml"
    experiment.write_text("patients: [42]\n", encoding="utf-8")
    selection_root = tmp_path / "selection"
    _write_selection(selection_root, experiment)

    experiment.write_text("patients: [43]\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="experiment config does not match",
    ):
        load_selected_post_rt_candidate(
            selection_root=selection_root,
            experiment_config_path=experiment,
        )
