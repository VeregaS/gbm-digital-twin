from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

POST_RT_SELECTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class PostRTSelectionConfig:
    initial_kill_rates_per_day: tuple[float, ...]
    decay_times_days: tuple[float, ...]
    include_fractionated_only_baseline: bool = True

    def __post_init__(self) -> None:
        if not self.initial_kill_rates_per_day:
            raise ValueError(
                "initial_kill_rates_per_day cannot be empty"
            )

        if not self.decay_times_days:
            raise ValueError(
                "decay_times_days cannot be empty"
            )

        if any(
            value <= 0.0
            for value in self.initial_kill_rates_per_day
        ):
            raise ValueError(
                "Post-RT kill rates must be positive"
            )

        if any(
            value <= 0.0
            for value in self.decay_times_days
        ):
            raise ValueError(
                "Post-RT decay times must be positive"
            )


def _require_mapping(
    value: object,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return value


def _require_list(
    value: object,
    name: str,
) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(
            f"{name} must be a list"
        )

    return value


def load_post_rt_selection_config(
    path: Path,
) -> PostRTSelectionConfig:
    if not path.is_file():
        raise FileNotFoundError(
            f"Post-RT selection config not found: {path}"
        )

    raw: object = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    root = _require_mapping(
        raw,
        "post-RT selection config",
    )

    schema_version = root.get(
        "schema_version"
    )

    if schema_version != POST_RT_SELECTION_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported post-RT selection config schema"
        )

    raw_rates = _require_list(
        root.get(
            "initial_kill_rates_per_day"
        ),
        "initial_kill_rates_per_day",
    )

    raw_decay_times = _require_list(
        root.get(
            "decay_times_days"
        ),
        "decay_times_days",
    )

    include_baseline = root.get(
        "include_fractionated_only_baseline",
        True,
    )

    if type(include_baseline) is not bool:
        raise ValueError(
            "include_fractionated_only_baseline must be boolean"
        )

    return PostRTSelectionConfig(
        initial_kill_rates_per_day=tuple(
            float(value)
            for value in raw_rates
        ),
        decay_times_days=tuple(
            float(value)
            for value in raw_decay_times
        ),
        include_fractionated_only_baseline=(
            include_baseline
        ),
    )
