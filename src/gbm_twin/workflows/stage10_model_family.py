from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from gbm_twin.workflows.stage9_model_family import (
    Stage9DelayedCandidate,
)

Stage10CandidateKind = Literal[
    "stage9-control",
    "decoupled",
]


@dataclass(frozen=True)
class Stage10Candidate:
    candidate_id: str
    kind: Stage10CandidateKind
    damage_half_life_days: float
    complexity_rank: int

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError(
                "candidate_id cannot be empty"
            )

        if self.damage_half_life_days <= 0.0:
            raise ValueError(
                "damage_half_life_days must be positive"
            )

        if self.complexity_rank < 0:
            raise ValueError(
                "complexity_rank must be non-negative"
            )


def control_candidate(
    selected_stage9: Stage9DelayedCandidate,
) -> Stage10Candidate:
    if (
        abs(
            selected_stage9
            .damage_transfer_fraction
            - 1.0
        )
        > 1e-12
        or abs(
            selected_stage9
            .damaged_visibility
            - 1.0
        )
        > 1e-12
    ):
        raise ValueError(
            "Stage 10 requires the selected Stage 9 control "
            "to use transfer=1 and visibility=1"
        )

    return Stage10Candidate(
        candidate_id=(
            "stage10-stage9-control"
        ),
        kind="stage9-control",
        damage_half_life_days=(
            selected_stage9
            .damage_half_life_days
        ),
        complexity_rank=(
            selected_stage9
            .complexity_rank
        ),
    )


def decoupled_candidates(
    half_life_days: tuple[
        float,
        ...,
    ],
) -> tuple[
    Stage10Candidate,
    ...,
]:
    if not half_life_days:
        raise ValueError(
            "Stage 10 half-life grid cannot be empty"
        )

    if len(
        set(
            half_life_days
        )
    ) != len(
        half_life_days
    ):
        raise ValueError(
            "Stage 10 half-life grid contains duplicates"
        )

    return tuple(
        Stage10Candidate(
            candidate_id=(
                "stage10-decoupled"
                f"-half-life-{value:g}d"
            ),
            kind="decoupled",
            damage_half_life_days=(
                value
            ),
            complexity_rank=2,
        )
        for value in half_life_days
    )


def build_stage10_candidates(
    *,
    selected_stage9: Stage9DelayedCandidate,
    half_life_days: tuple[
        float,
        ...,
    ],
) -> tuple[
    Stage10Candidate,
    ...,
]:
    return (
        control_candidate(
            selected_stage9
        ),
        *decoupled_candidates(
            half_life_days
        ),
    )
