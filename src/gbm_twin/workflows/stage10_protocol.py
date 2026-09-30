from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml


@dataclass(frozen=True)
class Stage10SelectionConfig:
    catastrophic_delta_vs_persistence: float
    max_mean_dice_degradation: float
    max_growth_delta_degradation: float
    min_regression_delta_gain: float


@dataclass(frozen=True)
class Stage10ProtocolConfig:
    schema_version: int
    design: str
    visible_damage_half_life_days: tuple[
        float,
        ...,
    ]
    selection: Stage10SelectionConfig

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError(
                "Unsupported Stage 10 protocol schema version"
            )

        if (
            self.design
            != "frozen_stage9_kinetics_decoupled_damage_v1"
        ):
            raise ValueError(
                "Unsupported Stage 10 design"
            )

        if not self.visible_damage_half_life_days:
            raise ValueError(
                "Stage 10 half-life grid cannot be empty"
            )

        if len(
            set(
                self.visible_damage_half_life_days
            )
        ) != len(
            self.visible_damage_half_life_days
        ):
            raise ValueError(
                "Stage 10 half-life grid contains duplicates"
            )

        if any(
            (
                not math.isfinite(
                    value
                )
                or value <= 0.0
            )
            for value in (
                self.visible_damage_half_life_days
            )
        ):
            raise ValueError(
                "Stage 10 half-lives must be finite and positive"
            )

        if (
            not math.isfinite(
                self.selection
                .catastrophic_delta_vs_persistence
            )
            or self.selection
            .catastrophic_delta_vs_persistence
            >= 0.0
        ):
            raise ValueError(
                "catastrophic_delta_vs_persistence must be finite and negative"
            )

        for name, value in (
            (
                "max_mean_dice_degradation",
                self.selection
                .max_mean_dice_degradation,
            ),
            (
                "max_growth_delta_degradation",
                self.selection
                .max_growth_delta_degradation,
            ),
            (
                "min_regression_delta_gain",
                self.selection
                .min_regression_delta_gain,
            ),
        ):
            if (
                not math.isfinite(
                    value
                )
                or value < 0.0
            ):
                raise ValueError(
                    f"{name} must be finite and non-negative"
                )


def _mapping(
    value: object,
    *,
    name: str,
) -> dict[str, object]:
    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(
        key
    )

    if type(value) is not int:
        raise ValueError(
            f"{key} must be an integer"
        )

    return cast(
        int,
        value,
    )


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
            f"{key} must be numeric"
        )

    return float(
        value
    )


def _float_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[
    float,
    ...,
]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"{key} must be a list"
        )

    result: list[
        float
    ] = []

    for item in value:
        if (
            isinstance(
                item,
                bool,
            )
            or not isinstance(
                item,
                (int, float),
            )
        ):
            raise ValueError(
                f"{key} must contain numeric values"
            )

        result.append(
            float(
                item
            )
        )

    return tuple(
        result
    )


def load_stage10_protocol_config(
    path: Path,
) -> Stage10ProtocolConfig:
    if not path.is_file():
        raise FileNotFoundError(
            path
        )

    raw: object = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    root = _mapping(
        raw,
        name="Stage 10 protocol",
    )

    design = root.get(
        "design"
    )

    if (
        not isinstance(
            design,
            str,
        )
        or not design
    ):
        raise ValueError(
            "design must be a non-empty string"
        )

    decoupled = _mapping(
        root.get(
            "decoupled"
        ),
        name="decoupled",
    )

    selection = _mapping(
        root.get(
            "selection"
        ),
        name="selection",
    )

    return Stage10ProtocolConfig(
        schema_version=_int(
            root,
            "schema_version",
        ),
        design=design,
        visible_damage_half_life_days=(
            _float_tuple(
                decoupled,
                "visible_damage_half_life_days",
            )
        ),
        selection=(
            Stage10SelectionConfig(
                catastrophic_delta_vs_persistence=(
                    _float(
                        selection,
                        "catastrophic_delta_vs_persistence",
                    )
                ),
                max_mean_dice_degradation=(
                    _float(
                        selection,
                        "max_mean_dice_degradation",
                    )
                ),
                max_growth_delta_degradation=(
                    _float(
                        selection,
                        "max_growth_delta_degradation",
                    )
                ),
                min_regression_delta_gain=(
                    _float(
                        selection,
                        "min_regression_delta_gain",
                    )
                ),
            )
        ),
    )
