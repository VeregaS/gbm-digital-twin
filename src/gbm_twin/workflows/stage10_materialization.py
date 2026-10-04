"""Prepare only a verified sealed reserve cohort; never decode MRI outcomes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_data_audit import load_sealed_stage8_data_audit
from gbm_twin.workflows.stage8_materialization import (
    MaterializationMode,
    Stage8MaterializationResult,
    _materialize_one,
    _same_existing_file,
    _source_error,
    _source_issues,
    build_stage8_materialization_plan,
    resolve_stage8_source_data_root,
)
from gbm_twin.workflows.stage8_selection_artifact import load_selected_stage8_model
from gbm_twin.workflows.stage10_selection_artifact import load_selected_stage10_model
from gbm_twin.workflows.stage10_validation_plan import (
    load_stage10_validation_plan,
    select_stage10_reserve_patient_ids,
)
from gbm_twin.workflows.stage10_validation_protocol import (
    load_stage10_validation_config,
    verify_frozen_stage10_model,
)


def materialize_stage10_reserve(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    data_audit_root: Path,
    stage8_selection_root: Path,
    stage10_selection_root: Path,
    frozen_model_config_path: Path,
    validation_config_path: Path,
    validation_plan_root: Path,
    source_data_root: Path | None = None,
    mode: MaterializationMode = "auto",
    dry_run: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Stage8MaterializationResult:
    if mode not in {"auto", "hardlink", "copy"}:
        raise ValueError(f"Unsupported materialization mode: {mode}")

    # Complete the seal/provenance checks before inspecting any patient files.
    plan = load_stage10_validation_plan(validation_plan_root)
    audit = load_sealed_stage8_data_audit(data_audit_root)
    stage8 = load_selected_stage8_model(stage8_selection_root)
    selected = load_selected_stage10_model(stage10_selection_root)
    verify_frozen_stage10_model(selected=selected, config_path=frozen_model_config_path)
    validation = load_stage10_validation_config(validation_config_path)
    audit_sha = sha256_file(data_audit_root / "stage8_data_audit.json")
    stage8_sha = sha256_file(stage8_selection_root / "stage8_model_selection.json")
    checks = (
        (stage8.stage8_data_audit_sha256, audit_sha),
        (selected.stage8_data_audit_sha256, audit_sha),
        (selected.stage8_model_selection_sha256, stage8_sha),
        (selected.stage8_protocol_sha256, sha256_file(stage8_protocol_path)),
        (selected.experiment_config_sha256, sha256_file(experiment_config_path)),
        (plan.stage8_data_audit_sha256, audit_sha),
        (plan.stage10_selection_sha256, selected.source_manifest_sha256),
        (plan.frozen_model_config_sha256, sha256_file(frozen_model_config_path)),
        (plan.validation_config_sha256, sha256_file(validation_config_path)),
    )
    if any(actual != expected for actual, expected in checks):
        raise ValueError("Stage 10 materialization provenance mismatch")
    expected_ids = select_stage10_reserve_patient_ids(
        audit_manifest=audit.manifest,
        reserve_patient_ids=selected.reserve_patient_ids,
        untouched_holdout_patient_ids=selected.untouched_holdout_patient_ids,
        count=validation.patient_count,
        seed=validation.seed,
    )
    if (
        plan.patient_ids != expected_ids
        or plan.seed != validation.seed
        or plan.remaining_reserve_patient_ids
        != tuple(sorted(set(selected.reserve_patient_ids) - set(expected_ids)))
        or plan.untouched_holdout_patient_ids != selected.untouched_holdout_patient_ids
    ):
        raise ValueError("Stage 10 sealed cohort differs from the prespecified reserve plan")

    experiment = load_cohort_experiment_config(experiment_config_path)
    patients = experiment.patients_root
    destination = (patients if patients.is_absolute() else repo_root / patients).resolve()
    source = resolve_stage8_source_data_root(explicit=source_data_root, patients_root=destination)
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError("Source and prepared patient roots must be separate, non-nested trees")
    items = build_stage8_materialization_plan(
        source_root=source,
        destination_root=destination,
        patient_ids=plan.patient_ids,
        require_spatial_rtdose=stage8.candidate.use_spatial_rtdose,
    )
    issues = _source_issues(items)
    if issues:
        raise FileNotFoundError(
            _source_error(source, issues).replace("Stage 8", "Stage 10")
            + "\nExtract the official NIfTI release or pass --source-data-root. "
            "The sealed cohort will not be replaced."
        )
    # Check ALL conflicts before writing anything. An interrupted run can be resumed.
    reused = []
    for item in items:
        if not item.source_path.resolve().is_relative_to(source):
            raise ValueError(f"Source input escapes source root: {item.source_path}")
        if not item.destination_path.resolve().is_relative_to(destination):
            raise ValueError(f"Destination input escapes prepared root: {item.destination_path}")
        if item.destination_path.exists() and not item.destination_path.is_file():
            raise ValueError(f"Destination is not a file: {item.destination_path}")
        reused.append(_same_existing_file(item.source_path, item.destination_path))

    counts = {"hardlink": 0, "copy": 0}
    for item, exists in zip(items, reused, strict=True):
        action = "reused" if exists else "planned"
        if not exists and not dry_run:
            action = _materialize_one(item.source_path, item.destination_path, mode=mode)
            counts[action] += 1
        if progress:
            progress(f"[stage10-materialize] patient={item.patient_id} {item.input_name}: {action}")
    return Stage8MaterializationResult(
        source_root=source,
        destination_root=destination,
        patient_ids=plan.patient_ids,
        required_count=len(items),
        created_count=sum(counts.values()),
        reused_count=sum(reused),
        hardlink_count=counts["hardlink"],
        copy_count=counts["copy"],
        dry_run=dry_run,
    )
