from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import sha256_file

_SELECTION_SCHEMA_VERSION = 1
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SelectedPostRTCandidate:
    candidate_id: str
    initial_kill_rate_per_day: float
    decay_time_days: float

    source_manifest_sha256: str
    selection_config_sha256: str
    experiment_config_sha256: str

    def to_provenance_payload(self) -> dict[str, object]:
        return {
            "kind": "sealed_post_rt_parameter_selection",
            "candidate_id": self.candidate_id,
            "initial_kill_rate_per_day": (
                self.initial_kill_rate_per_day
            ),
            "decay_time_days": self.decay_time_days,
            "source_manifest_sha256": (
                self.source_manifest_sha256
            ),
            "selection_config_sha256": (
                self.selection_config_sha256
            ),
            "experiment_config_sha256": (
                self.experiment_config_sha256
            ),
        }


def _require_mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            f"Post-RT selection field {key!r} must be a mapping"
        )

    return cast(dict[str, object], value)


def _require_string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str):
        raise ValueError(
            f"Post-RT selection field {key!r} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"Post-RT selection field {key!r} must not be empty"
        )

    return normalized


def _require_sha256(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = _require_string(mapping, key)

    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ValueError(
            f"Post-RT selection field {key!r} must be SHA-256"
        )

    return value


def _require_positive_float(
    mapping: dict[str, object],
    key: str,
) -> float:
    raw = mapping.get(key)

    if (
        isinstance(raw, bool)
        or not isinstance(raw, (int, float))
    ):
        raise ValueError(
            f"Post-RT selection field {key!r} must be numeric"
        )

    value = float(raw)

    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(
            f"Post-RT selection field {key!r} must be finite and positive"
        )

    return value


def load_selected_post_rt_candidate(
    *,
    selection_root: Path,
    experiment_config_path: Path,
) -> SelectedPostRTCandidate:
    root = selection_root.resolve()
    manifest_path = root / "post_rt_selection.json"
    seal_path = root / "post_rt_selection.sha256"

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Post-RT selection manifest not found: {manifest_path}"
        )

    if not seal_path.is_file():
        raise FileNotFoundError(
            f"Post-RT selection seal not found: {seal_path}"
        )

    tokens = seal_path.read_text(encoding="ascii").split()
    if not tokens:
        raise ValueError("Post-RT selection seal is empty")

    expected_sha256 = tokens[0]
    actual_sha256 = sha256_file(manifest_path)
    if expected_sha256 != actual_sha256:
        raise ValueError(
            "Post-RT selection manifest checksum mismatch"
        )

    raw: object = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    if not isinstance(raw, dict):
        raise ValueError(
            "Post-RT selection manifest must contain a JSON object"
        )

    manifest = cast(dict[str, object], raw)

    if manifest.get("schema_version") != _SELECTION_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported post-RT selection schema version"
        )
    if manifest.get("kind") != "v3_post_rt_parameter_selection":
        raise ValueError(
            "Artifact is not a V3 post-RT parameter selection"
        )
    if manifest.get("sealed") is not True:
        raise ValueError("Post-RT selection artifact is not sealed")

    repository = _require_mapping(manifest, "repository")
    if repository.get("dirty") is not False:
        raise ValueError(
            "Post-RT selection must come from a clean Git working tree"
        )

    leakage = _require_mapping(manifest, "leakage_control")
    if leakage.get("loads_t2_imaging") is not False:
        raise ValueError(
            "Post-RT selection does not satisfy the t2 leakage contract"
        )
    if leakage.get("uses_timepoints") != ["t0", "t1"]:
        raise ValueError(
            "Post-RT selection must use exactly t0 and t1"
        )
    if (
        leakage.get("selection_metric")
        != "mean_t0_t1_calibration_loss"
    ):
        raise ValueError(
            "Unsupported post-RT selection metric"
        )

    experiment = _require_mapping(manifest, "experiment")
    artifact_experiment_sha256 = _require_sha256(
        experiment,
        "experiment_config_sha256",
    )
    current_experiment_sha256 = sha256_file(
        experiment_config_path.resolve()
    )
    if artifact_experiment_sha256 != current_experiment_sha256:
        raise ValueError(
            "Post-RT selection experiment config does not match "
            "the V3 freeze experiment config"
        )

    selected = _require_mapping(manifest, "selected_candidate")
    candidate_id = _require_string(selected, "candidate_id")
    if candidate_id == "fractionated-only":
        raise ValueError(
            "Selected treatment candidate has no delayed post-RT effect"
        )

    return SelectedPostRTCandidate(
        candidate_id=candidate_id,
        initial_kill_rate_per_day=_require_positive_float(
            selected,
            "initial_kill_rate_per_day",
        ),
        decay_time_days=_require_positive_float(
            selected,
            "decay_time_days",
        ),
        source_manifest_sha256=actual_sha256,
        selection_config_sha256=_require_sha256(
            experiment,
            "selection_config_sha256",
        ),
        experiment_config_sha256=artifact_experiment_sha256,
    )
