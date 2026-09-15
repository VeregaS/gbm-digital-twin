from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RiskSeverity = Literal[
    "high",
    "moderate",
]


@dataclass(frozen=True)
class AtlasRegionDefinition:
    label: int

    name: str
    category: str

    laterality: str | None = None
    functional_note: str | None = None


@dataclass(frozen=True)
class AnatomicalWarning:
    severity: RiskSeverity

    region_label: int
    region_name: str
    category: str

    laterality: str | None
    functional_note: str | None

    observed_overlap_cm3: float
    latent_overlap_cm3: float

    min_observed_distance_mm: float | None

    message: str


@dataclass(frozen=True)
class AnatomicalRiskReport:
    patient_id: int
    timepoint_name: str

    configured: bool

    atlas_name: str | None
    status_message: str

    latent_level: float
    proximity_threshold_mm: float

    warnings: tuple[
        AnatomicalWarning,
        ...,
    ]

    disclaimer: str = (
        "Research-only atlas proximity analysis. "
        "Atlas-defined functional associations do not "
        "establish patient-specific functional anatomy."
    )

    @property
    def high_count(self) -> int:
        return sum(
            warning.severity == "high"
            for warning in self.warnings
        )

    @property
    def moderate_count(self) -> int:
        return sum(
            warning.severity == "moderate"
            for warning in self.warnings
        )
