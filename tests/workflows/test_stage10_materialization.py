from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gbm_twin.workflows import stage10_materialization as workflow
from gbm_twin.workflows import stage10_validation as validation_workflow
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage10_validation_plan import select_stage10_reserve_patient_ids


@pytest.fixture
def cohort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    paths = {}
    for name in ("audit", "stage8", "stage10", "plan"):
        paths[name] = tmp_path / name
        paths[name].mkdir()
    for name, filename in (
        ("audit", "stage8_data_audit.json"),
        ("stage8", "stage8_model_selection.json"),
    ):
        (paths[name] / filename).write_text("{}")
    for name in ("experiment", "protocol", "frozen", "validation"):
        paths[name] = tmp_path / f"{name}.yaml"
        paths[name].write_text(name)
    rows = {
        "patients": [
            {"patient_id": pid, "split": "development", "split_stratum": "same"}
            for pid in (15, 47, 57)
        ]
    }
    ids = select_stage10_reserve_patient_ids(
        audit_manifest=rows,
        reserve_patient_ids=(15, 47, 57),
        untouched_holdout_patient_ids=(99,),
        count=2,
        seed=2026,
    )
    audit_sha = sha256_file(paths["audit"] / "stage8_data_audit.json")
    selected = SimpleNamespace(
        stage8_data_audit_sha256=audit_sha,
        stage8_model_selection_sha256=sha256_file(paths["stage8"] / "stage8_model_selection.json"),
        stage8_protocol_sha256=sha256_file(paths["protocol"]),
        experiment_config_sha256=sha256_file(paths["experiment"]),
        source_manifest_sha256="selection-sha",
        reserve_patient_ids=(15, 47, 57),
        untouched_holdout_patient_ids=(99,),
    )
    payload = {
        "schema_version": 1,
        "kind": "stage10_reserve_validation_plan",
        "sealed": True,
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "stage10_selection_sha256": selected.source_manifest_sha256,
            "frozen_model_config_sha256": sha256_file(paths["frozen"]),
            "validation_config_sha256": sha256_file(paths["validation"]),
        },
        "selection_rule": {"seed": 2026},
        "patient_ids": list(ids),
        "remaining_reserve_patient_ids": sorted(set((15, 47, 57)) - set(ids)),
        "untouched_holdout_patient_ids": [99],
        "leakage_control": {
            "reserve_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "selection_uses_metadata_only": True,
            "global_model_parameters_changed": False,
        },
    }
    manifest = paths["plan"] / "stage10_validation_plan.json"
    manifest.write_text(json.dumps(payload))
    (paths["plan"] / "stage10_validation_plan.sha256").write_text(sha256_file(manifest))
    monkeypatch.setattr(
        workflow, "load_sealed_stage8_data_audit", lambda _: SimpleNamespace(manifest=rows)
    )
    monkeypatch.setattr(
        workflow,
        "load_selected_stage8_model",
        lambda _: SimpleNamespace(
            stage8_data_audit_sha256=audit_sha, candidate=SimpleNamespace(use_spatial_rtdose=False)
        ),
    )
    monkeypatch.setattr(workflow, "load_selected_stage10_model", lambda _: selected)
    monkeypatch.setattr(workflow, "verify_frozen_stage10_model", lambda **_: None)
    monkeypatch.setattr(
        workflow,
        "load_stage10_validation_config",
        lambda _: SimpleNamespace(patient_count=2, seed=2026),
    )
    monkeypatch.setattr(
        workflow,
        "load_cohort_experiment_config",
        lambda _: SimpleNamespace(patients_root=tmp_path / "patients"),
    )
    # Invalid NIfTI bytes prove that materialization never decodes images.
    for pid in (15, 47, 57, 99):
        for tp in ("t0", "t1", "t2"):
            folder = tmp_path / "data" / str(pid) / tp
            folder.mkdir(parents=True)
            for suffix in ("t1gd", "gtv", "brain_mask"):
                (folder / f"{pid}_{tp}_{suffix}.nii.gz").write_bytes(b"opaque-not-a-nifti")
    kwargs = dict(
        repo_root=tmp_path,
        experiment_config_path=paths["experiment"],
        stage8_protocol_path=paths["protocol"],
        data_audit_root=paths["audit"],
        stage8_selection_root=paths["stage8"],
        stage10_selection_root=paths["stage10"],
        frozen_model_config_path=paths["frozen"],
        validation_config_path=paths["validation"],
        validation_plan_root=paths["plan"],
        source_data_root=tmp_path / "data",
    )
    return kwargs, ids, selected


@pytest.mark.parametrize("mode", ["auto", "copy", "hardlink"])
def test_exact_sealed_cohort_and_idempotent_resume(cohort, mode):
    kwargs, ids, _ = cohort
    first = workflow.materialize_stage10_reserve(**kwargs, mode=mode)
    assert first.patient_ids == ids
    assert first.created_count == 18
    assert {int(p.name) for p in first.destination_root.iterdir()} == set(ids)
    second = workflow.materialize_stage10_reserve(**kwargs, mode=mode)
    assert second.created_count == 0
    assert second.reused_count == 18


def test_dry_run_leaves_destination_absent(cohort):
    kwargs, _, _ = cohort
    result = workflow.materialize_stage10_reserve(**kwargs, dry_run=True)
    assert result.required_count == 18
    assert result.created_count == 0
    assert not result.destination_root.exists()


def test_missing_source_does_not_prepare_partial_cohort(cohort):
    kwargs, ids, _ = cohort
    (kwargs["source_data_root"] / str(ids[-1]) / "t2" / f"{ids[-1]}_t2_gtv.nii.gz").unlink()
    with pytest.raises(FileNotFoundError, match="will not be replaced"):
        workflow.materialize_stage10_reserve(**kwargs)
    assert not (kwargs["repo_root"] / "patients").exists()


def test_conflicting_last_input_prevents_earlier_writes(cohort):
    kwargs, ids, _ = cohort
    dest = kwargs["repo_root"] / "patients" / str(ids[-1]) / "t2"
    dest.mkdir(parents=True)
    (dest / f"{ids[-1]}_t2_brain_mask.nii.gz").write_bytes(b"conflict")
    with pytest.raises(ValueError, match="different size"):
        workflow.materialize_stage10_reserve(**kwargs)
    assert not (kwargs["repo_root"] / "patients" / str(ids[0])).exists()


def test_tampered_seal_rejected_before_data_access(cohort, monkeypatch):
    kwargs, _, _ = cohort
    (kwargs["validation_plan_root"] / "stage10_validation_plan.json").write_text("{}")
    monkeypatch.setattr(
        workflow,
        "build_stage8_materialization_plan",
        lambda **_: pytest.fail("Patient data accessed before seal check"),
    )
    with pytest.raises(ValueError, match="checksum"):
        workflow.materialize_stage10_reserve(**kwargs)


def test_provenance_mismatch_rejected_before_data_access(cohort, monkeypatch):
    kwargs, _, selected = cohort
    selected.experiment_config_sha256 = "changed"
    monkeypatch.setattr(
        workflow,
        "build_stage8_materialization_plan",
        lambda **_: pytest.fail("Patient data accessed before provenance check"),
    )
    with pytest.raises(ValueError, match="provenance"):
        workflow.materialize_stage10_reserve(**kwargs)


def test_resealed_substituted_patient_is_rejected(cohort):
    kwargs, ids, _ = cohort
    manifest = kwargs["validation_plan_root"] / "stage10_validation_plan.json"
    payload = json.loads(manifest.read_text())
    payload["patient_ids"] = [ids[0], 99]
    manifest.write_text(json.dumps(payload))
    (manifest.parent / "stage10_validation_plan.sha256").write_text(sha256_file(manifest))
    with pytest.raises(ValueError, match="prespecified reserve plan"):
        workflow.materialize_stage10_reserve(**kwargs)


def test_direct_validation_rejects_resealed_subset_before_patient_access(cohort, monkeypatch):
    kwargs, ids, selected = cohort
    selection = kwargs["stage10_selection_root"] / "stage10_decoupled_selection.json"
    selection.write_text("{}")
    selected.source_manifest_sha256 = sha256_file(selection)
    manifest = kwargs["validation_plan_root"] / "stage10_validation_plan.json"
    payload = json.loads(manifest.read_text())
    payload["source"]["stage10_selection_sha256"] = selected.source_manifest_sha256
    payload["patient_ids"] = list(ids[:1])
    manifest.write_text(json.dumps(payload))
    (manifest.parent / "stage10_validation_plan.sha256").write_text(sha256_file(manifest))
    for name in (
        "load_sealed_stage8_data_audit", "load_selected_stage8_model",
        "load_selected_stage10_model", "verify_frozen_stage10_model",
        "load_stage10_validation_config",
    ):
        monkeypatch.setattr(validation_workflow, name, getattr(workflow, name))
    monkeypatch.setattr(
        validation_workflow, "read_repository_state", lambda _: SimpleNamespace(dirty=False),
    )
    monkeypatch.setattr(
        validation_workflow, "load_cohort_experiment_config",
        lambda _: pytest.fail("Patient configuration accessed before cohort check"),
    )
    direct_kwargs = {key: value for key, value in kwargs.items() if key != "source_data_root"}
    with pytest.raises(ValueError, match="prespecified reserve plan"):
        validation_workflow.validate_stage10_model(
            **direct_kwargs, cache_root=kwargs["repo_root"] / "cache",
            output_dir=kwargs["repo_root"] / "result",
        )
    assert not (kwargs["repo_root"] / "result").exists()


def test_auto_falls_back_to_copy(cohort, monkeypatch):
    kwargs, _, _ = cohort

    def fail_link(*args):
        raise OSError("cross-device link")

    monkeypatch.setattr("gbm_twin.workflows.stage8_materialization.os.link", fail_link)
    result = workflow.materialize_stage10_reserve(**kwargs)
    assert result.copy_count == 18
    assert result.hardlink_count == 0


def test_download_cannot_start_before_sealed_plan_verification(cohort, monkeypatch):
    kwargs, _, _ = cohort
    (kwargs["validation_plan_root"] / "stage10_validation_plan.json").write_text("{}")
    monkeypatch.setattr(
        workflow, "acquire_cfb_files", lambda **_: pytest.fail("Download before seal verification")
    )
    with pytest.raises(ValueError, match="checksum"):
        workflow.materialize_stage10_reserve(**kwargs, download_missing=True)
