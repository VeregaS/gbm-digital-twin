from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)

STAGE8_VALIDATION_PLAN_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Stage8ValidationPlan:
    directory: Path
    patient_ids: tuple[int, ...]
    data_audit_sha256: str
    model_selection_sha256: str
    requested_count: int
    seed: int


def _candidate_rows(
    manifest: dict[str, object],
) -> list[dict[str, object]]:
    raw_patients = manifest.get("patients")
    if not isinstance(raw_patients, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    rows: list[dict[str, object]] = []
    for raw in raw_patients:
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")
        if raw.get("split") not in {"development", "internal-validation"}:
            continue
        if raw.get("core_eligible") is not True:
            continue
        if raw.get("exposed_development") is True:
            continue
        rows.append(cast(dict[str, object], raw))

    if not rows:
        raise ValueError(
            "Stage 8 audit contains no internal-validation candidates"
        )
    return rows


def _patient_id(row: dict[str, object]) -> int:
    value = row.get("patient_id")
    if type(value) is not int:
        raise ValueError("Stage 8 audit patient_id must be an integer")
    return cast(int, value)


def _stratum(row: dict[str, object]) -> str:
    value = row.get("split_stratum")
    if not isinstance(value, str) or not value:
        raise ValueError("Stage 8 audit split_stratum is missing")
    return value


def _rank(seed: int, stratum: str, patient_id: int) -> str:
    payload = (
        f"stage8-internal-validation-v1:{seed}:{stratum}:{patient_id}"
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def select_validation_patient_ids(
    manifest: dict[str, object],
    *,
    count: int,
    seed: int,
) -> tuple[int, ...]:
    if count < 1:
        raise ValueError("Stage 8 validation patient count must be positive")

    rows = _candidate_rows(manifest)
    if count > len(rows):
        raise ValueError(
            "Stage 8 validation patient count exceeds the eligible cohort"
        )

    groups: dict[str, list[int]] = {}
    for row in rows:
        groups.setdefault(_stratum(row), []).append(_patient_id(row))

    ordered_groups: dict[str, list[int]] = {
        stratum: sorted(
            patient_ids,
            key=lambda patient_id: _rank(seed, stratum, patient_id),
        )
        for stratum, patient_ids in sorted(groups.items())
    }
    selected: dict[str, list[int]] = {
        stratum: []
        for stratum in ordered_groups
    }

    # If possible, preserve every metadata-only stratum in the compact cohort.
    if count >= len(ordered_groups):
        for stratum, patient_ids in ordered_groups.items():
            selected[stratum].append(patient_ids[0])

    while sum(len(values) for values in selected.values()) < count:
        eligible_strata = [
            stratum
            for stratum, patient_ids in ordered_groups.items()
            if len(selected[stratum]) < len(patient_ids)
        ]
        if not eligible_strata:
            break

        stratum = min(
            eligible_strata,
            key=lambda name: (
                len(selected[name]) / len(ordered_groups[name]),
                name,
            ),
        )
        next_index = len(selected[stratum])
        selected[stratum].append(ordered_groups[stratum][next_index])

    result = tuple(
        sorted(
            patient_id
            for patient_ids in selected.values()
            for patient_id in patient_ids
        )
    )
    if len(result) != count:
        raise RuntimeError("Failed to construct Stage 8 validation cohort")
    return result


def _required_relative_paths(
    patient_ids: tuple[int, ...],
    *,
    require_spatial_rtdose: bool,
) -> tuple[str, ...]:
    paths: list[str] = []

    for patient_id in patient_ids:
        for timepoint in ("t0", "t1", "t2"):
            prefix = f"{patient_id}_{timepoint}"
            for suffix in ("t1gd", "gtv", "brain_mask"):
                paths.append(
                    f"{patient_id}/{timepoint}/{prefix}_{suffix}.nii.gz"
                )

        if require_spatial_rtdose:
            paths.append(f"{patient_id}/**/*rtdose*.nii.gz")

    return tuple(paths)


def create_stage8_validation_plan(
    *,
    data_audit_root: Path,
    selection_root: Path,
    output_dir: Path,
    patient_count: int = 16,
    seed: int = 20260919,
) -> Stage8ValidationPlan:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Stage 8 validation-plan destination exists: {destination}"
        )

    audit = load_sealed_stage8_data_audit(data_audit_root)
    selected_model = load_selected_stage8_model(selection_root)
    audit_manifest = (
        data_audit_root.resolve() / "stage8_data_audit.json"
    )
    audit_sha = sha256_file(audit_manifest)

    if selected_model.stage8_data_audit_sha256 != audit_sha:
        raise ValueError(
            "Selected Stage 8 model does not match the sealed data audit"
        )

    patient_ids = select_validation_patient_ids(
        audit.manifest,
        count=patient_count,
        seed=seed,
    )
    rows_by_id = {
        _patient_id(row): row
        for row in _candidate_rows(audit.manifest)
    }
    selected_rows = [rows_by_id[patient_id] for patient_id in patient_ids]

    required_paths = _required_relative_paths(
        patient_ids,
        require_spatial_rtdose=(
            selected_model.candidate.use_spatial_rtdose
        ),
    )

    payload: dict[str, object] = {
        "schema_version": STAGE8_VALIDATION_PLAN_SCHEMA_VERSION,
        "kind": "stage8_internal_validation_plan",
        "sealed": True,
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "stage8_model_selection_sha256": (
                selected_model.source_manifest_sha256
            ),
        },
        "selection_rule": {
            "method": "deterministic_stratified_compact_v1",
            "seed": seed,
            "requested_patient_count": patient_count,
            "stratification": ["model_tier", "rt_regimen"],
            "uses_outcomes": False,
            "loads_t2_image_content": False,
        },
        "patient_ids": list(patient_ids),
        "patients": [
            {
                "patient_id": _patient_id(row),
                "model_tier": row.get("model_tier"),
                "split_stratum": row.get("split_stratum"),
                "rt_total_dose_gy": row.get("rt_total_dose_gy"),
                "rt_fractions": row.get("rt_fractions"),
            }
            for row in selected_rows
        ],
        "reserve_patient_ids": sorted(
            _patient_id(row)
            for row in _candidate_rows(audit.manifest)
            if _patient_id(row) not in set(patient_ids)
        ),
        "leakage_control": {
            "internal_validation_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "selection_uses_metadata_only": True,
        },
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )
    try:
        manifest_path = temporary / "stage8_validation_plan.json"
        manifest_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (temporary / "stage8_validation_plan.sha256").write_text(
            sha256_file(manifest_path)
            + "  stage8_validation_plan.json\n",
            encoding="ascii",
        )
        (temporary / "stage8_validation_patient_ids.txt").write_text(
            "\n".join(str(patient_id) for patient_id in patient_ids) + "\n",
            encoding="ascii",
        )
        (temporary / "stage8_validation_required_paths.txt").write_text(
            "\n".join(required_paths) + "\n",
            encoding="utf-8",
        )
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return load_stage8_validation_plan(destination)


def _mapping(mapping: dict[str, object], key: str) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Stage 8 validation plan field {key!r} is invalid")
    return cast(dict[str, object], value)


def _string(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Stage 8 validation plan field {key!r} is invalid")
    return value


def load_stage8_validation_plan(
    directory: Path,
) -> Stage8ValidationPlan:
    root = directory.resolve()
    manifest_path = root / "stage8_validation_plan.json"
    seal_path = root / "stage8_validation_plan.sha256"

    if not manifest_path.is_file() or not seal_path.is_file():
        raise FileNotFoundError("Stage 8 validation-plan artifact is incomplete")

    tokens = seal_path.read_text(encoding="ascii").split()
    if not tokens or tokens[0] != sha256_file(manifest_path):
        raise ValueError("Stage 8 validation-plan checksum mismatch")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Stage 8 validation plan must be a JSON object")
    manifest = cast(dict[str, object], raw)

    if manifest.get("schema_version") != STAGE8_VALIDATION_PLAN_SCHEMA_VERSION:
        raise ValueError("Unsupported Stage 8 validation-plan schema")
    if manifest.get("kind") != "stage8_internal_validation_plan":
        raise ValueError("Artifact is not a Stage 8 validation plan")
    if manifest.get("sealed") is not True:
        raise ValueError("Stage 8 validation plan is not sealed")

    leakage = _mapping(manifest, "leakage_control")
    if leakage.get("internal_validation_t2_loaded") is not False:
        raise ValueError("Validation plan violates internal-validation leakage")
    if leakage.get("untouched_holdout_t2_loaded") is not False:
        raise ValueError("Validation plan violates holdout leakage")
    if leakage.get("selection_uses_metadata_only") is not True:
        raise ValueError("Validation plan was not selected from metadata only")

    raw_ids = manifest.get("patient_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ValueError("Stage 8 validation plan has no patient IDs")
    patient_ids: list[int] = []
    for value in raw_ids:
        if type(value) is not int:
            raise ValueError("Stage 8 validation patient ID must be integer")
        patient_ids.append(cast(int, value))

    rule = _mapping(manifest, "selection_rule")
    count = rule.get("requested_patient_count")
    seed = rule.get("seed")
    if type(count) is not int or type(seed) is not int:
        raise ValueError("Stage 8 validation-plan selection rule is invalid")

    source = _mapping(manifest, "source")
    return Stage8ValidationPlan(
        directory=root,
        patient_ids=tuple(patient_ids),
        data_audit_sha256=_string(
            source,
            "stage8_data_audit_sha256",
        ),
        model_selection_sha256=_string(
            source,
            "stage8_model_selection_sha256",
        ),
        requested_count=cast(int, count),
        seed=cast(int, seed),
    )
