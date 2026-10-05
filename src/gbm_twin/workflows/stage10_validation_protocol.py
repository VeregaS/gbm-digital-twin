from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml

from gbm_twin.workflows.provenance import (
    sha256_file,
)
from gbm_twin.workflows.stage10_selection_artifact import (
    SelectedStage10Model,
)


@dataclass(frozen=True)
class FrozenStage10ModelConfig:
    schema_version: int
    model_id: str
    selection_artifact_sha256: str
    candidate_kind: str
    visible_damage_half_life_days: float


@dataclass(frozen=True)
class Stage10ValidationConfig:
    schema_version: int
    design: str
    patient_count: int
    seed: int
    selection_method: str
    catastrophic_delta_vs_persistence: float
    bootstrap_samples: int
    bootstrap_seed: int
    min_mean_delta_vs_persistence: float
    min_median_delta_vs_persistence: float
    max_catastrophic_failure_count: int
    require_mean_rve_not_worse_than_persistence: bool
    require_mean_hd95_not_worse_than_persistence: bool
    next_step_if_passed: str
    next_step_if_failed: str


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
            f"{key} must be a mapping"
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
        or not value.strip()
    ):
        raise ValueError(
            f"{key} must be a non-empty string"
        )

    return value.strip()


def _integer(
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
            f"{key} must be an integer"
        )

    return cast(
        int,
        value,
    )


def _number(
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
            f"{key} must be numeric"
        )

    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{key} must be finite")
    return result


def _boolean(
    mapping: dict[str, object],
    key: str,
) -> bool:
    value = mapping.get(
        key
    )

    if type(
        value
    ) is not bool:
        raise ValueError(
            f"{key} must be boolean"
        )

    return cast(
        bool,
        value,
    )


def _load_yaml(
    path: Path,
) -> dict[str, object]:
    raw: object = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            f"{path} must contain a mapping"
        )

    return cast(
        dict[str, object],
        raw,
    )


def load_frozen_stage10_model_config(
    path: Path,
) -> FrozenStage10ModelConfig:
    payload = _load_yaml(
        path.resolve()
    )

    structure = _mapping(
        payload,
        "structure",
    )

    selection = _mapping(
        payload,
        "selection_artifact",
    )

    result = FrozenStage10ModelConfig(
        schema_version=_integer(
            payload,
            "schema_version",
        ),
        model_id=_string(
            payload,
            "model_id",
        ),
        selection_artifact_sha256=(
            _string(
                selection,
                "sha256",
            )
        ),
        candidate_kind=_string(
            structure,
            "kind",
        ),
        visible_damage_half_life_days=(
            _number(
                structure,
                "visible_damage_half_life_days",
            )
        ),
    )

    if result.schema_version != 1:
        raise ValueError(
            "Unsupported frozen Stage 10 model schema"
        )

    if result.candidate_kind != "decoupled":
        raise ValueError(
            "Frozen Stage 10 model must be decoupled"
        )

    if (
        result.visible_damage_half_life_days
        <= 0.0
    ):
        raise ValueError(
            "Frozen Stage 10 half-life must be positive"
        )

    return result


def verify_frozen_stage10_model(
    *,
    selected: SelectedStage10Model,
    config_path: Path,
) -> FrozenStage10ModelConfig:
    frozen = (
        load_frozen_stage10_model_config(
            config_path
        )
    )

    if (
        selected.source_manifest_sha256
        != frozen.selection_artifact_sha256
    ):
        raise ValueError(
            "Stage 10 selection does not match the frozen artifact SHA-256"
        )

    if (
        selected.candidate.candidate_id
        != frozen.model_id
    ):
        raise ValueError(
            "Stage 10 selected candidate does not match frozen model_id"
        )

    if (
        selected.candidate.kind
        != frozen.candidate_kind
    ):
        raise ValueError(
            "Stage 10 selected candidate kind does not match freeze"
        )

    if (
        abs(
            selected
            .candidate
            .damage_half_life_days
            - frozen
            .visible_damage_half_life_days
        )
        > 1e-12
    ):
        raise ValueError(
            "Stage 10 selected half-life does not match freeze"
        )

    return frozen


def load_stage10_validation_config(
    path: Path,
) -> Stage10ValidationConfig:
    payload = _load_yaml(
        path.resolve()
    )

    cohort = _mapping(
        payload,
        "cohort",
    )

    evaluation = _mapping(
        payload,
        "evaluation",
    )

    advancement = _mapping(
        payload,
        "advancement",
    )

    next_step = _mapping(
        payload,
        "next_step",
    )

    result = Stage10ValidationConfig(
        schema_version=_integer(
            payload,
            "schema_version",
        ),
        design=_string(
            payload,
            "design",
        ),
        patient_count=_integer(
            cohort,
            "patient_count",
        ),
        seed=_integer(
            cohort,
            "seed",
        ),
        selection_method=_string(
            cohort,
            "selection_method",
        ),
        catastrophic_delta_vs_persistence=(
            _number(
                evaluation,
                "catastrophic_delta_vs_persistence",
            )
        ),
        bootstrap_samples=_integer(
            evaluation,
            "bootstrap_samples",
        ),
        bootstrap_seed=_integer(
            evaluation,
            "bootstrap_seed",
        ),
        min_mean_delta_vs_persistence=(
            _number(
                advancement,
                "min_mean_delta_vs_persistence",
            )
        ),
        min_median_delta_vs_persistence=(
            _number(
                advancement,
                "min_median_delta_vs_persistence",
            )
        ),
        max_catastrophic_failure_count=(
            _integer(
                advancement,
                "max_catastrophic_failure_count",
            )
        ),
        require_mean_rve_not_worse_than_persistence=(
            _boolean(
                advancement,
                "require_mean_rve_not_worse_than_persistence",
            )
        ),
        require_mean_hd95_not_worse_than_persistence=(
            _boolean(
                advancement,
                "require_mean_hd95_not_worse_than_persistence",
            )
        ),
        next_step_if_passed=_string(
            next_step,
            "if_passed",
        ),
        next_step_if_failed=_string(
            next_step,
            "if_failed",
        ),
    )

    if result.schema_version != 1:
        raise ValueError(
            "Unsupported Stage 10 validation protocol schema"
        )

    if result.patient_count <= 0:
        raise ValueError(
            "Stage 10 validation patient_count must be positive"
        )

    if result.bootstrap_samples <= 0:
        raise ValueError(
            "Stage 10 bootstrap_samples must be positive"
        )

    if (
        result
        .max_catastrophic_failure_count
        < 0
    ):
        raise ValueError(
            "Stage 10 catastrophic failure limit must be non-negative"
        )

    return result


def stage10_validation_config_sha256(
    path: Path,
) -> str:
    return sha256_file(
        path.resolve()
    )
