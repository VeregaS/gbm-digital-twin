from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionTarget:
    timepoint_name: str
    target_day: float

    def __post_init__(self) -> None:
        if not isinstance(
            self.timepoint_name,
            str,
        ):
            raise TypeError(
                "Prediction target timepoint "
                "name must be a string"
            )

        timepoint_name = (
            self.timepoint_name.strip()
        )

        if not timepoint_name:
            raise ValueError(
                "Prediction target timepoint "
                "name must not be empty"
            )

        try:
            target_day = float(
                self.target_day
            )
        except (
            TypeError,
            ValueError,
        ) as exc:
            raise TypeError(
                "Prediction target day must "
                "be a real number"
            ) from exc

        if not math.isfinite(
            target_day
        ):
            raise ValueError(
                "Prediction target day must "
                "be finite"
            )

        object.__setattr__(
            self,
            "timepoint_name",
            timepoint_name,
        )

        object.__setattr__(
            self,
            "target_day",
            target_day,
        )