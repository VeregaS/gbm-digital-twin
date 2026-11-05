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
from gbm_twin.workflows.stage9_selection_artifact import (
    load_selected_stage9_model,
)

STAGE9_VALIDATION_PLAN_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Stage9ValidationPlan:
    directory: Path
    patient_ids: tuple[int, ...]
    reserve_patient_ids: tuple[int, ...]
    stage9_selection_sha256: str
    stage8_data_audit_sha256: str
    seed: int


def _patient_rows(
    manifest: dict[str, object],
) -> dict[int, dict[str, object]]:
    raw = manifest.get("patients")
    if not isinstance(raw, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    rows: dict[int, dict[str, object]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")
        row = cast(dict[str, object], item)
        patient_id = row.get("patient_id")
        if type(patient_id) is not int:
            raise ValueError("Stage 8 audit patient_id must be integer")
        rows[cast(int, patient_id)] = row

    return rows


def _stratum(row: dict[str, object]) -> str:
    value = row.get("split_stratum")
    if not isinstance(value, str) or not value:
        raise ValueError("Stage 8 audit split_stratum is missing")
    return value


def _rank(seed: int, stratum: str, patient_id: int) -> str:
    payload = f"stage9-reserve-validation:{seed}:{stratum}:{patient_id}"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def select_stage9_reserve_patient_ids(
    *,
    audit_manifest: dict[str, object],
    reserve_patient_ids: tuple[int, ...],
    count: int,
    seed: int,
) -> tuple[int, ...]:
    if count < 1:
        raise ValueError("Stage 9 validation patient count must be positive")
    if count > len(reserve_patient_ids):
        raise ValueError(
            "Stage 9 validation patient count exceeds reserve cohort"
        )

    rows = _patient_rows(audit_manifest)
    groups: dict[str, list[int]] = {}

    for patient_id in reserve_patient_ids:
        row = rows.get(patient_id)
        if row is None:
            raise ValueError(
                f"Reserve patient {patient_id} is absent from data audit"
            )
        if row.get("split") == "untouched-holdout":
            raise ValueError(
                f"Reserve patient {patient_id} is in untouched holdout"
            )
        groups.setdefault(_stratum(row), []).append(patient_id)

    ordered: dict[str, list[int]] = {
        stratum: sorted(
            patient_ids,
            key=lambda patient_id: _rank(
                seed,
                stratum,
                patient_id,
            ),
        )
        for stratum, patient_ids in sorted(groups.items())
    }
    selected: dict[str, list[int]] = {
        stratum: []
        for stratum in ordered
    }

    if count >= len(ordered):
        for stratum, patient_ids in ordered.items():
            selected[stratum].append(patient_ids[0])

    while sum(len(values) for values in selected.values()) < count:
        eligible = [
            stratum
            for stratum, patient_ids in ordered.items()
            if len(selected[stratum]) < len(patient_ids)
        ]
        if not eligible:
            break

        stratum = min(
            eligible,
            key=lambda name: (
                len(selected[name]) / len(ordered[name]),
                name,
            ),
        )
        selected[stratum].append(
            ordered[stratum][len(selected[stratum])]
        )

    result = tuple(
        sorted(
            patient_id
            for values in selected.values()
            for patient_id in values
        )
    )
    if len(result) != count:
        raise RuntimeError("Failed to construct Stage 9 validation cohort")
    return result


def _required_paths(
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


def create_stage9_validation_plan(
    *,
    data_audit_root: Path,
    stage9_selection_root: Path,
    output_dir: Path,
    patient_count: int = 16,
    seed: int = 20260920,
) -> Stage9ValidationPlan:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Stage 9 validation-plan destination exists: {destination}"
        )

    audit = load_sealed_stage8_data_audit(data_audit_root)
    selected = load_selected_stage9_model(stage9_selection_root)
    audit_sha = sha256_file(
        data_audit_root.resolve() / "stage8_data_audit.json"
    )
    if selected.stage8_data_audit_sha256 != audit_sha:
        raise ValueError(
            "Stage 9 selection does not match the sealed data audit"
        )

    patient_ids = select_stage9_reserve_patient_ids(
        audit_manifest=audit.manifest,
        reserve_patient_ids=selected.reserve_patient_ids,
        count=patient_count,
        seed=seed,
    )
    stage9_selection_sha = sha256_file(
        stage9_selection_root.resolve() / "stage9_delayed_selection.json"
    )

    payload: dict[str, object] = {
        "schema_version": STAGE9_VALIDATION_PLAN_SCHEMA_VERSION,
        "kind": "stage9_reserve_validation_plan",
        "sealed": True,
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "stage9_selection_sha256": stage9_selection_sha,
        },
        "selection_rule": {
            "method": "deterministic_stratified_reserve_v1",
            "seed": seed,
            "requested_patient_count": patient_count,
            "stratification": ["model_tier", "rt_regimen"],
            "uses_outcomes": False,
            "loads_t2_image_content": False,
        },
        "patient_ids": list(patient_ids),
        "remaining_reserve_patient_ids": sorted(
            set(selected.reserve_patient_ids) - set(patient_ids)
        ),
        "untouched_holdout_patient_ids": list(
            selected.untouched_holdout_patient_ids
        ),
        "leakage_control": {
            "reserve_t2_loaded": False,
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
        manifest_path = temporary / "stage9_validation_plan.json"
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
        (temporary / "stage9_validation_plan.sha256").write_text(
            sha256_file(manifest_path)
            + "  stage9_validation_plan.json\n",
            encoding="ascii",
        )
        (temporary / "stage9_validation_patient_ids.txt").write_text(
            "\n".join(str(value) for value in patient_ids) + "\n",
            encoding="ascii",
        )
        (temporary / "stage9_validation_required_paths.txt").write_text(
            "\n".join(
                _required_paths(
                    patient_ids,
                    require_spatial_rtdose=(
                        selected.base_stage8_use_spatial_rtdose
                    ),
                )
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return load_stage9_validation_plan(destination)


def _mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Stage 9 plan field {key!r} must be a mapping")
    return cast(dict[str, object], value)


def _string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Stage 9 plan field {key!r} must be string")
    return value


def _int_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[int, ...]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Stage 9 plan field {key!r} must be list")

    result: list[int] = []
    for item in value:
        if type(item) is not int:
            raise ValueError(
                f"Stage 9 plan field {key!r} must contain integers"
            )
        result.append(cast(int, item))
    return tuple(result)


def load_stage9_validation_plan(
    directory: Path,
) -> Stage9ValidationPlan:
    root = directory.resolve()
    manifest_path = root / "stage9_validation_plan.json"
    seal_path = root / "stage9_validation_plan.sha256"

    if not manifest_path.is_file() or not seal_path.is_file():
        raise FileNotFoundError("Stage 9 validation plan is incomplete")

    tokens = seal_path.read_text(encoding="ascii").split()
    if not tokens or tokens[0] != sha256_file(manifest_path):
        raise ValueError("Stage 9 validation-plan checksum mismatch")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Stage 9 validation plan must be JSON object")
    manifest = cast(dict[str, object], raw)

    if manifest.get("schema_version") != STAGE9_VALIDATION_PLAN_SCHEMA_VERSION:
        raise ValueError("Unsupported Stage 9 validation-plan schema")
    if manifest.get("kind") != "stage9_reserve_validation_plan":
        raise ValueError("Artifact is not a Stage 9 validation plan")
    if manifest.get("sealed") is not True:
        raise ValueError("Stage 9 validation plan is not sealed")

    leakage = _mapping(manifest, "leakage_control")
    if leakage.get("reserve_t2_loaded") is not False:
        raise ValueError("Stage 9 reserve t2 was already loaded")
    if leakage.get("untouched_holdout_t2_loaded") is not False:
        raise ValueError("Stage 9 holdout t2 was already loaded")
    if leakage.get("selection_uses_metadata_only") is not True:
        raise ValueError("Stage 9 validation plan used outcomes")

    source = _mapping(manifest, "source")
    rule = _mapping(manifest, "selection_rule")
    seed = rule.get("seed")
    if type(seed) is not int:
        raise ValueError("Stage 9 validation-plan seed must be integer")

    return Stage9ValidationPlan(
        directory=root,
        patient_ids=_int_tuple(manifest, "patient_ids"),
        reserve_patient_ids=_int_tuple(
            manifest,
            "remaining_reserve_patient_ids",
        ),
        stage9_selection_sha256=_string(
            source,
            "stage9_selection_sha256",
        ),
        stage8_data_audit_sha256=_string(
            source,
            "stage8_data_audit_sha256",
        ),
        seed=cast(int, seed),
    )
