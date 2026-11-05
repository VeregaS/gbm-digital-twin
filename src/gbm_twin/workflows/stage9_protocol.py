from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml


@dataclass(frozen=True)
class Stage9DelayedResponseConfig:
    half_life_days: tuple[float, ...]
    transfer_fractions: tuple[float, ...]
    visibility_values: tuple[float, ...]


@dataclass(frozen=True)
class Stage9SelectionConfig:
    catastrophic_delta_vs_persistence: float
    min_mean_dice_gain_over_stage8_control: float
    max_additional_catastrophic_failures: int


@dataclass(frozen=True)
class Stage9ProtocolConfig:
    schema_version: int
    design: str
    delayed: Stage9DelayedResponseConfig
    selection: Stage9SelectionConfig

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Unsupported Stage 9 protocol schema version")
        if self.design != "frozen_stage8_kinetics_delayed_response_v1":
            raise ValueError("Unsupported Stage 9 design")

        for values, name in (
            (self.delayed.half_life_days, "damage_half_life_days"),
            (self.delayed.transfer_fractions, "damage_transfer_fraction"),
            (self.delayed.visibility_values, "damaged_visibility"),
        ):
            if not values:
                raise ValueError(f"{name} cannot be empty")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} contains duplicates")

        if any(
            not math.isfinite(value) or value <= 0.0
            for value in self.delayed.half_life_days
        ):
            raise ValueError(
                "damage_half_life_days must be finite and positive"
            )
        if any(
            not math.isfinite(value) or not 0.0 < value <= 1.0
            for value in self.delayed.transfer_fractions
        ):
            raise ValueError(
                "damage_transfer_fraction must be within (0, 1]"
            )
        if any(
            not math.isfinite(value) or not 0.0 < value <= 1.0
            for value in self.delayed.visibility_values
        ):
            raise ValueError("damaged_visibility must be within (0, 1]")

        if (
            self.selection.catastrophic_delta_vs_persistence >= 0.0
            or not math.isfinite(
                self.selection.catastrophic_delta_vs_persistence
            )
        ):
            raise ValueError(
                "catastrophic_delta_vs_persistence must be finite "
                "and negative"
            )
        if (
            self.selection.min_mean_dice_gain_over_stage8_control < 0.0
            or not math.isfinite(
                self.selection.min_mean_dice_gain_over_stage8_control
            )
        ):
            raise ValueError(
                "min_mean_dice_gain_over_stage8_control must be "
                "finite and non-negative"
            )
        if self.selection.max_additional_catastrophic_failures < 0:
            raise ValueError(
                "max_additional_catastrophic_failures must be non-negative"
            )


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return cast(dict[str, object], value)


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


def _float_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[float, ...]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")

    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{key} must contain numeric values")
        result.append(float(item))
    return tuple(result)


def load_stage9_protocol_config(path: Path) -> Stage9ProtocolConfig:
    if not path.is_file():
        raise FileNotFoundError(path)

    raw: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = _mapping(raw, name="Stage 9 protocol")
    design = root.get("design")
    if not isinstance(design, str) or not design:
        raise ValueError("design must be a non-empty string")

    delayed = _mapping(
        root.get("delayed_response"),
        name="delayed_response",
    )
    selection = _mapping(root.get("selection"), name="selection")

    return Stage9ProtocolConfig(
        schema_version=_int(root, "schema_version"),
        design=design,
        delayed=Stage9DelayedResponseConfig(
            half_life_days=_float_tuple(
                delayed,
                "damage_half_life_days",
            ),
            transfer_fractions=_float_tuple(
                delayed,
                "damage_transfer_fraction",
            ),
            visibility_values=_float_tuple(
                delayed,
                "damaged_visibility",
            ),
        ),
        selection=Stage9SelectionConfig(
            catastrophic_delta_vs_persistence=_float(
                selection,
                "catastrophic_delta_vs_persistence",
            ),
            min_mean_dice_gain_over_stage8_control=_float(
                selection,
                "min_mean_dice_gain_over_stage8_control",
            ),
            max_additional_catastrophic_failures=_int(
                selection,
                "max_additional_catastrophic_failures",
            ),
        ),
    )
