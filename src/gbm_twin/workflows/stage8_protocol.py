from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml


@dataclass(frozen=True)
class Stage8ObservationConfig:
    enhancing_detection_threshold: float
    infiltrative_detection_threshold: float
    transition_width_mm: float

    def __post_init__(self) -> None:
        if not 0.0 < self.infiltrative_detection_threshold < 1.0:
            raise ValueError(
                "infiltrative_detection_threshold must be within (0, 1)"
            )

        if not 0.0 < self.enhancing_detection_threshold < 1.0:
            raise ValueError(
                "enhancing_detection_threshold must be within (0, 1)"
            )

        if (
            self.infiltrative_detection_threshold
            >= self.enhancing_detection_threshold
        ):
            raise ValueError(
                "infiltrative threshold must be lower than enhancing threshold"
            )

        if self.transition_width_mm <= 0.0:
            raise ValueError("transition_width_mm must be positive")


@dataclass(frozen=True)
class Stage8RadiobiologyConfig:
    alpha_beta_ratio_gy: float
    effective_alpha_candidates_per_gy: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.alpha_beta_ratio_gy <= 0.0:
            raise ValueError("alpha_beta_ratio_gy must be positive")

        if not self.effective_alpha_candidates_per_gy:
            raise ValueError(
                "effective_alpha_candidates_per_gy cannot be empty"
            )

        if any(
            value <= 0.0
            for value in self.effective_alpha_candidates_per_gy
        ):
            raise ValueError(
                "effective alpha candidates must be positive"
            )

        if (
            len(set(self.effective_alpha_candidates_per_gy))
            != len(self.effective_alpha_candidates_per_gy)
        ):
            raise ValueError("effective alpha candidates contain duplicates")


@dataclass(frozen=True)
class Stage8TreatmentMemoryConfig:
    enabled: bool
    proliferation_survival_candidates: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.proliferation_survival_candidates:
            raise ValueError(
                "proliferation_survival_candidates cannot be empty"
            )

        for value in self.proliferation_survival_candidates:
            if not 0.0 < value <= 1.0:
                raise ValueError(
                    "proliferation survival candidates must be within (0, 1]"
                )

        if (
            len(set(self.proliferation_survival_candidates))
            != len(self.proliferation_survival_candidates)
        ):
            raise ValueError(
                "proliferation survival candidates contain duplicates"
            )


@dataclass(frozen=True)
class Stage8ProtocolConfig:
    schema_version: int
    exposed_development_patient_ids: tuple[int, ...]
    holdout_fraction: float
    split_seed: int
    required_timepoints: tuple[str, ...]
    required_modalities: tuple[str, ...]
    preferred_modalities: tuple[str, ...]
    require_complete_rt_schedule: bool
    require_rtdose: bool
    observation: Stage8ObservationConfig
    radiobiology: Stage8RadiobiologyConfig
    chemotherapy_enabled: bool
    treatment_memory: Stage8TreatmentMemoryConfig

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Unsupported Stage 8 protocol schema version")

        if not 0.0 < self.holdout_fraction < 1.0:
            raise ValueError("holdout_fraction must be within (0, 1)")

        if self.split_seed < 0:
            raise ValueError("split_seed must be non-negative")

        if not self.required_timepoints:
            raise ValueError("required_timepoints cannot be empty")

        if not self.required_modalities:
            raise ValueError("required_modalities cannot be empty")

        if len(set(self.required_timepoints)) != len(self.required_timepoints):
            raise ValueError("required_timepoints contains duplicates")

        if len(set(self.required_modalities)) != len(self.required_modalities):
            raise ValueError("required_modalities contains duplicates")

        if len(set(self.preferred_modalities)) != len(self.preferred_modalities):
            raise ValueError("preferred_modalities contains duplicates")

        if (
            len(set(self.exposed_development_patient_ids))
            != len(self.exposed_development_patient_ids)
        ):
            raise ValueError(
                "exposed_development_patient_ids contains duplicates"
            )


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")

    return cast(dict[str, object], value)


def _list(value: object, *, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")

    return cast(list[object], value)


def _int(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)

    if type(value) is not int:
        raise ValueError(f"{key} must be an integer")

    return cast(int, value)


def _float(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")

    return float(value)


def _bool(mapping: dict[str, object], key: str) -> bool:
    value = mapping.get(key)

    if type(value) is not bool:
        raise ValueError(f"{key} must be boolean")

    return cast(bool, value)


def _str_tuple(mapping: dict[str, object], key: str) -> tuple[str, ...]:
    result: list[str] = []

    for raw in _list(mapping.get(key), name=key):
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"{key} must contain non-empty strings")

        result.append(raw.strip().lower())

    return tuple(result)


def _int_tuple(mapping: dict[str, object], key: str) -> tuple[int, ...]:
    result: list[int] = []

    for raw in _list(mapping.get(key), name=key):
        if type(raw) is not int:
            raise ValueError(f"{key} must contain integers")

        result.append(cast(int, raw))

    return tuple(result)


def _float_tuple(mapping: dict[str, object], key: str) -> tuple[float, ...]:
    result: list[float] = []

    for raw in _list(mapping.get(key), name=key):
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{key} must contain numeric values")

        result.append(float(raw))

    return tuple(result)


def load_stage8_protocol_config(path: Path) -> Stage8ProtocolConfig:
    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = _mapping(raw, name="Stage 8 protocol")

    observation_raw = _mapping(
        root.get("observation_model"),
        name="observation_model",
    )
    radiobiology_raw = _mapping(
        root.get("radiobiology"),
        name="radiobiology",
    )
    chemotherapy_raw = _mapping(
        root.get("chemotherapy"),
        name="chemotherapy",
    )
    treatment_memory_raw = _mapping(
        root.get("treatment_memory"),
        name="treatment_memory",
    )

    return Stage8ProtocolConfig(
        schema_version=_int(root, "schema_version"),
        exposed_development_patient_ids=_int_tuple(
            root,
            "exposed_development_patient_ids",
        ),
        holdout_fraction=_float(root, "holdout_fraction"),
        split_seed=_int(root, "split_seed"),
        required_timepoints=_str_tuple(root, "required_timepoints"),
        required_modalities=_str_tuple(root, "required_modalities"),
        preferred_modalities=_str_tuple(root, "preferred_modalities"),
        require_complete_rt_schedule=_bool(
            root,
            "require_complete_rt_schedule",
        ),
        require_rtdose=_bool(root, "require_rtdose"),
        observation=Stage8ObservationConfig(
            enhancing_detection_threshold=_float(
                observation_raw,
                "enhancing_detection_threshold",
            ),
            infiltrative_detection_threshold=_float(
                observation_raw,
                "infiltrative_detection_threshold",
            ),
            transition_width_mm=_float(
                observation_raw,
                "transition_width_mm",
            ),
        ),
        radiobiology=Stage8RadiobiologyConfig(
            alpha_beta_ratio_gy=_float(
                radiobiology_raw,
                "alpha_beta_ratio_gy",
            ),
            effective_alpha_candidates_per_gy=_float_tuple(
                radiobiology_raw,
                "effective_alpha_candidates_per_gy",
            ),
        ),
        chemotherapy_enabled=_bool(chemotherapy_raw, "enabled"),
        treatment_memory=Stage8TreatmentMemoryConfig(
            enabled=_bool(treatment_memory_raw, "enabled"),
            proliferation_survival_candidates=_float_tuple(
                treatment_memory_raw,
                "proliferation_survival_candidates",
            ),
        ),
    )
