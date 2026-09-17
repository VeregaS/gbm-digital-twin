from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_model_family import Stage8ModelCandidate

STAGE8_SELECTION_SCHEMA_VERSION = 1
STAGE8_SELECTION_DESIGN = "sequential_nested_ablation_v1"


@dataclass(frozen=True)
class SelectedStage8Model:
    candidate: Stage8ModelCandidate
    source_manifest_sha256: str
    stage8_data_audit_sha256: str
    protocol_config_sha256: str
    experiment_config_sha256: str
    repository_commit_sha: str
    selection_design: str

    def provenance_payload(self) -> dict[str, object]:
        return {
            "kind": "sealed_stage8_model_selection",
            "selection_design": self.selection_design,
            "candidate_id": self.candidate.candidate_id,
            "use_spatial_rtdose": self.candidate.use_spatial_rtdose,
            "effective_alpha_per_gy": (
                self.candidate.effective_alpha_per_gy
            ),
            "alpha_beta_ratio_gy": self.candidate.alpha_beta_ratio_gy,
            "proliferation_survival": (
                self.candidate.proliferation_survival
            ),
            "use_infiltrative_observation": (
                self.candidate.use_infiltrative_observation
            ),
            "source_manifest_sha256": self.source_manifest_sha256,
            "stage8_data_audit_sha256": self.stage8_data_audit_sha256,
            "protocol_config_sha256": self.protocol_config_sha256,
            "experiment_config_sha256": self.experiment_config_sha256,
            "repository_commit_sha": self.repository_commit_sha,
        }


def _mapping(mapping: dict[str, object], key: str) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Stage 8 selection field {key!r} must be a mapping")
    return cast(dict[str, object], value)


def _string(mapping: dict[str, object], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"Stage 8 selection field {key!r} must be a non-empty string"
        )
    return value.strip()


def _boolean(mapping: dict[str, object], key: str) -> bool:
    value = mapping.get(key)
    if type(value) is not bool:
        raise ValueError(f"Stage 8 selection field {key!r} must be boolean")
    return cast(bool, value)


def _positive_float(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Stage 8 selection field {key!r} must be numeric")

    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(
            f"Stage 8 selection field {key!r} must be finite and positive"
        )
    return result


def _unit_interval_positive(mapping: dict[str, object], key: str) -> float:
    value = _positive_float(mapping, key)
    if value > 1.0:
        raise ValueError(
            f"Stage 8 selection field {key!r} must not exceed 1"
        )
    return value


def load_selected_stage8_model(
    selection_root: Path,
) -> SelectedStage8Model:
    root = selection_root.resolve()
    manifest_path = root / "stage8_model_selection.json"
    seal_path = root / "stage8_model_selection.sha256"

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Stage 8 selection manifest not found: {manifest_path}"
        )
    if not seal_path.is_file():
        raise FileNotFoundError(
            f"Stage 8 selection seal not found: {seal_path}"
        )

    tokens = seal_path.read_text(encoding="ascii").split()
    if not tokens:
        raise ValueError("Stage 8 selection seal is empty")

    actual_sha256 = sha256_file(manifest_path)
    if tokens[0] != actual_sha256:
        raise ValueError("Stage 8 model-selection checksum mismatch")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Stage 8 selection must contain a JSON object")
    manifest = cast(dict[str, object], raw)

    if manifest.get("schema_version") != STAGE8_SELECTION_SCHEMA_VERSION:
        raise ValueError("Unsupported Stage 8 selection schema version")
    if manifest.get("kind") != "stage8_development_model_selection":
        raise ValueError("Artifact is not a Stage 8 model selection")
    if manifest.get("sealed") is not True:
        raise ValueError("Stage 8 model selection is not sealed")

    selection_rule = _mapping(manifest, "selection_rule")
    design = _string(selection_rule, "design")
    if design != STAGE8_SELECTION_DESIGN:
        raise ValueError(
            f"Unsupported Stage 8 model-selection design: {design}"
        )

    leakage = _mapping(manifest, "leakage_control")
    if leakage.get("untouched_holdout_t2_loaded") is not False:
        raise ValueError(
            "Stage 8 selection violates untouched-holdout leakage contract"
        )
    if leakage.get("internal_validation_t2_loaded") is not False:
        raise ValueError(
            "Stage 8 selection violates internal-validation leakage contract"
        )
    if (
        leakage.get("candidate_selection_uses_only_development_exposed")
        is not True
    ):
        raise ValueError(
            "Stage 8 selection did not use the declared development cohort"
        )

    repository = _mapping(manifest, "repository")
    if _boolean(repository, "dirty"):
        raise ValueError(
            "Sealed Stage 8 model selection must come from a clean Git tree"
        )

    source = _mapping(manifest, "source")
    selected = _mapping(manifest, "selected_candidate")
    candidate = Stage8ModelCandidate(
        candidate_id=_string(selected, "candidate_id"),
        use_spatial_rtdose=_boolean(selected, "use_spatial_rtdose"),
        effective_alpha_per_gy=_positive_float(
            selected,
            "effective_alpha_per_gy",
        ),
        alpha_beta_ratio_gy=_positive_float(
            selected,
            "alpha_beta_ratio_gy",
        ),
        proliferation_survival=_unit_interval_positive(
            selected,
            "proliferation_survival",
        ),
        use_infiltrative_observation=_boolean(
            selected,
            "use_infiltrative_observation",
        ),
    )

    return SelectedStage8Model(
        candidate=candidate,
        source_manifest_sha256=actual_sha256,
        stage8_data_audit_sha256=_string(
            source,
            "stage8_data_audit_sha256",
        ),
        protocol_config_sha256=_string(
            source,
            "protocol_config_sha256",
        ),
        experiment_config_sha256=_string(
            source,
            "experiment_config_sha256",
        ),
        repository_commit_sha=_string(repository, "commit_sha"),
        selection_design=design,
    )
