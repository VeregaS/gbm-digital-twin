from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage9_model_family import Stage9DelayedCandidate

STAGE9_SELECTION_SCHEMA_VERSION = 1
STAGE9_SELECTION_KIND = "stage9_delayed_response_development_selection"


@dataclass(frozen=True)
class SelectedStage9Model:
    candidate: Stage9DelayedCandidate
    source_manifest_sha256: str
    stage8_data_audit_sha256: str
    stage8_model_selection_sha256: str
    stage8_internal_validation_sha256: str
    stage8_protocol_sha256: str
    stage9_protocol_sha256: str
    experiment_config_sha256: str
    repository_commit_sha: str
    base_stage8_use_spatial_rtdose: bool
    reserve_patient_ids: tuple[int, ...]
    untouched_holdout_patient_ids: tuple[int, ...]


def _mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Stage 9 selection field {key!r} must be a mapping")
    return cast(dict[str, object], value)


def _string(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(
            f"Stage 9 selection field {key!r} must be a non-empty string"
        )
    return value


def _float(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Stage 9 selection field {key!r} must be numeric")
    return float(value)


def _int(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if type(value) is not int:
        raise ValueError(f"Stage 9 selection field {key!r} must be integer")
    return cast(int, value)


def _int_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[int, ...]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Stage 9 selection field {key!r} must be a list")

    result: list[int] = []
    for item in value:
        if type(item) is not int:
            raise ValueError(
                f"Stage 9 selection field {key!r} must contain integers"
            )
        result.append(cast(int, item))
    return tuple(result)


def load_selected_stage9_model(
    selection_root: Path,
) -> SelectedStage9Model:
    root = selection_root.resolve()
    manifest_path = root / "stage9_delayed_selection.json"
    seal_path = root / "stage9_delayed_selection.sha256"

    if not manifest_path.is_file() or not seal_path.is_file():
        raise FileNotFoundError("Stage 9 selection artifact is incomplete")

    tokens = seal_path.read_text(encoding="ascii").split()
    actual_sha = sha256_file(manifest_path)
    if not tokens or tokens[0] != actual_sha:
        raise ValueError("Stage 9 selection checksum mismatch")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Stage 9 selection must be a JSON object")
    manifest = cast(dict[str, object], raw)

    if manifest.get("schema_version") != STAGE9_SELECTION_SCHEMA_VERSION:
        raise ValueError("Unsupported Stage 9 selection schema")
    if manifest.get("kind") != STAGE9_SELECTION_KIND:
        raise ValueError("Artifact is not a Stage 9 delayed selection")
    if manifest.get("sealed") is not True:
        raise ValueError("Stage 9 selection is not sealed")

    repository = _mapping(manifest, "repository")
    if repository.get("dirty") is not False:
        raise ValueError(
            "Sealed Stage 9 selection must come from a clean Git tree"
        )

    leakage = _mapping(manifest, "leakage_control")
    if leakage.get("reserve_t2_loaded") is not False:
        raise ValueError("Stage 9 reserve t2 was already loaded")
    if leakage.get("untouched_holdout_t2_loaded") is not False:
        raise ValueError("Stage 9 untouched holdout t2 was already loaded")
    if leakage.get("patient_specific_kinetics_refit") is not False:
        raise ValueError("Stage 9 unexpectedly refit patient kinetics")

    selected = _mapping(manifest, "selected_candidate")
    candidate = Stage9DelayedCandidate(
        candidate_id=_string(selected, "candidate_id"),
        damage_transfer_fraction=_float(
            selected,
            "damage_transfer_fraction",
        ),
        damage_half_life_days=_float(
            selected,
            "damage_half_life_days",
        ),
        damaged_visibility=_float(
            selected,
            "damaged_visibility",
        ),
        complexity_rank=_int(selected, "complexity_rank"),
    )

    source = _mapping(manifest, "source")
    base_stage8 = _mapping(manifest, "base_stage8_candidate")
    use_spatial_rtdose = base_stage8.get("use_spatial_rtdose")
    if type(use_spatial_rtdose) is not bool:
        raise ValueError(
            "Stage 9 base Stage 8 spatial-dose flag must be boolean"
        )

    return SelectedStage9Model(
        candidate=candidate,
        source_manifest_sha256=actual_sha,
        stage8_data_audit_sha256=_string(
            source,
            "stage8_data_audit_sha256",
        ),
        stage8_model_selection_sha256=_string(
            source,
            "stage8_model_selection_sha256",
        ),
        stage8_internal_validation_sha256=_string(
            source,
            "stage8_internal_validation_sha256",
        ),
        stage8_protocol_sha256=_string(
            source,
            "stage8_protocol_sha256",
        ),
        stage9_protocol_sha256=_string(
            source,
            "stage9_protocol_sha256",
        ),
        experiment_config_sha256=_string(
            source,
            "experiment_config_sha256",
        ),
        repository_commit_sha=_string(repository, "commit_sha"),
        base_stage8_use_spatial_rtdose=cast(bool, use_spatial_rtdose),
        reserve_patient_ids=_int_tuple(
            leakage,
            "reserve_patient_ids",
        ),
        untouched_holdout_patient_ids=_int_tuple(
            leakage,
            "untouched_holdout_patient_ids",
        ),
    )
