from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from gbm_twin.workflows.provenance import (
    sha256_file,
)
from gbm_twin.workflows.stage10_model_family import (
    Stage10Candidate,
)
from gbm_twin.workflows.stage10_selection import (
    STAGE10_SELECTION_KIND,
    STAGE10_SELECTION_SCHEMA_VERSION,
)


@dataclass(frozen=True)
class SelectedStage10Model:
    candidate: Stage10Candidate
    source_manifest_sha256: str
    stage8_data_audit_sha256: str
    stage8_model_selection_sha256: str
    stage8_internal_validation_sha256: str
    stage9_selection_sha256: str
    reference_fidelity_v2_sha256: str
    stage8_protocol_sha256: str
    stage10_protocol_sha256: str
    experiment_config_sha256: str
    repository_commit_sha: str
    reserve_patient_ids: tuple[int, ...]
    untouched_holdout_patient_ids: tuple[int, ...]


def _mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"Stage 10 selection field {key!r} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(
        key
    )

    if (
        not isinstance(
            value,
            str,
        )
        or not value
    ):
        raise ValueError(
            f"Stage 10 selection field {key!r} must be a non-empty string"
        )

    return value


def _float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(
        key
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"Stage 10 selection field {key!r} must be numeric"
        )

    return float(
        value
    )


def _int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(
        key
    )

    if type(
        value
    ) is not int:
        raise ValueError(
            f"Stage 10 selection field {key!r} must be integer"
        )

    return cast(
        int,
        value,
    )


def _int_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[int, ...]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"Stage 10 selection field {key!r} must be a list"
        )

    result: list[int] = []

    for item in value:
        if type(
            item
        ) is not int:
            raise ValueError(
                f"Stage 10 selection field {key!r} must contain integers"
            )

        result.append(
            cast(
                int,
                item,
            )
        )

    return tuple(
        result
    )


def load_selected_stage10_model(
    selection_root: Path,
) -> SelectedStage10Model:
    root = (
        selection_root.resolve()
    )

    manifest_path = (
        root
        / "stage10_decoupled_selection.json"
    )

    seal_path = (
        root
        / "stage10_decoupled_selection.sha256"
    )

    if (
        not manifest_path.is_file()
        or not seal_path.is_file()
    ):
        raise FileNotFoundError(
            "Stage 10 selection artifact is incomplete"
        )

    tokens = seal_path.read_text(
        encoding="ascii"
    ).split()

    actual_sha = (
        sha256_file(
            manifest_path
        )
    )

    if (
        not tokens
        or tokens[0]
        != actual_sha
    ):
        raise ValueError(
            "Stage 10 selection checksum mismatch"
        )

    raw: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            "Stage 10 selection must be a JSON object"
        )

    manifest = cast(
        dict[str, object],
        raw,
    )

    if (
        manifest.get(
            "schema_version"
        )
        != STAGE10_SELECTION_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported Stage 10 selection schema"
        )

    if (
        manifest.get(
            "kind"
        )
        != STAGE10_SELECTION_KIND
    ):
        raise ValueError(
            "Artifact is not a Stage 10 selection"
        )

    if (
        manifest.get(
            "sealed"
        )
        is not True
    ):
        raise ValueError(
            "Stage 10 selection is not sealed"
        )

    if (
        manifest.get(
            "decision"
        )
        != "decoupled_candidate_advanced"
    ):
        raise ValueError(
            "Stage 10 selection did not advance a decoupled candidate"
        )

    repository = _mapping(
        manifest,
        "repository",
    )

    if (
        repository.get(
            "dirty"
        )
        is not False
    ):
        raise ValueError(
            "Sealed Stage 10 selection must come from a clean Git tree"
        )

    leakage = _mapping(
        manifest,
        "leakage_control",
    )

    required_flags = {
        "development_only": True,
        "reserve_t2_loaded": False,
        "untouched_holdout_t2_loaded": False,
        "patient_specific_kinetics_refit": False,
    }

    for (
        key,
        expected,
    ) in required_flags.items():
        if (
            leakage.get(
                key
            )
            is not expected
        ):
            raise ValueError(
                "Stage 10 leakage contract is inconsistent: "
                f"{key}"
            )

    selected = _mapping(
        manifest,
        "selected_candidate",
    )

    kind = _string(
        selected,
        "kind",
    )

    if kind != "decoupled":
        raise ValueError(
            "Selected Stage 10 candidate is not decoupled"
        )

    candidate = Stage10Candidate(
        candidate_id=_string(
            selected,
            "candidate_id",
        ),
        kind="decoupled",
        damage_half_life_days=_float(
            selected,
            "damage_half_life_days",
        ),
        complexity_rank=_int(
            selected,
            "complexity_rank",
        ),
    )

    source = _mapping(
        manifest,
        "source",
    )

    return SelectedStage10Model(
        candidate=candidate,
        source_manifest_sha256=(
            actual_sha
        ),
        stage8_data_audit_sha256=(
            _string(
                source,
                "stage8_data_audit_sha256",
            )
        ),
        stage8_model_selection_sha256=(
            _string(
                source,
                "stage8_model_selection_sha256",
            )
        ),
        stage8_internal_validation_sha256=(
            _string(
                source,
                "stage8_internal_validation_sha256",
            )
        ),
        stage9_selection_sha256=(
            _string(
                source,
                "stage9_selection_sha256",
            )
        ),
        reference_fidelity_v2_sha256=(
            _string(
                source,
                "reference_fidelity_v2_sha256",
            )
        ),
        stage8_protocol_sha256=(
            _string(
                source,
                "stage8_protocol_sha256",
            )
        ),
        stage10_protocol_sha256=(
            _string(
                source,
                "stage10_protocol_sha256",
            )
        ),
        experiment_config_sha256=(
            _string(
                source,
                "experiment_config_sha256",
            )
        ),
        repository_commit_sha=(
            _string(
                repository,
                "commit_sha",
            )
        ),
        reserve_patient_ids=_int_tuple(
            leakage,
            "reserve_patient_ids",
        ),
        untouched_holdout_patient_ids=(
            _int_tuple(
                leakage,
                "untouched_holdout_patient_ids",
            )
        ),
    )
