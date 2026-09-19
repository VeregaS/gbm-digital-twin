from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage9DelayedCandidate:
    candidate_id: str
    damage_transfer_fraction: float
    damage_half_life_days: float
    damaged_visibility: float
    complexity_rank: int

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id cannot be empty")
        if not 0.0 <= self.damage_transfer_fraction <= 1.0:
            raise ValueError(
                "damage_transfer_fraction must be within [0, 1]"
            )
        if self.damage_half_life_days <= 0.0:
            raise ValueError("damage_half_life_days must be positive")
        if not 0.0 <= self.damaged_visibility <= 1.0:
            raise ValueError("damaged_visibility must be within [0, 1]")
        if self.complexity_rank < 0:
            raise ValueError("complexity_rank must be non-negative")


def _id(
    *,
    transfer: float,
    half_life_days: float,
    visibility: float,
) -> str:
    return (
        "stage9-delayed"
        f"-transfer-{transfer:g}"
        f"-half-life-{half_life_days:g}d"
        f"-visibility-{visibility:g}"
    )


def control_candidate() -> Stage9DelayedCandidate:
    return Stage9DelayedCandidate(
        candidate_id="stage9-stage8-control",
        damage_transfer_fraction=0.0,
        damage_half_life_days=30.0,
        damaged_visibility=1.0,
        complexity_rank=0,
    )


def timescale_candidates(
    half_life_days: tuple[float, ...],
) -> tuple[Stage9DelayedCandidate, ...]:
    candidates = [control_candidate()]
    candidates.extend(
        Stage9DelayedCandidate(
            candidate_id=_id(
                transfer=1.0,
                half_life_days=value,
                visibility=1.0,
            ),
            damage_transfer_fraction=1.0,
            damage_half_life_days=value,
            damaged_visibility=1.0,
            complexity_rank=1,
        )
        for value in half_life_days
    )
    return tuple(candidates)


def transfer_candidates(
    *,
    half_life_days: float,
    transfer_values: tuple[float, ...],
) -> tuple[Stage9DelayedCandidate, ...]:
    return tuple(
        Stage9DelayedCandidate(
            candidate_id=_id(
                transfer=value,
                half_life_days=half_life_days,
                visibility=1.0,
            ),
            damage_transfer_fraction=value,
            damage_half_life_days=half_life_days,
            damaged_visibility=1.0,
            complexity_rank=2,
        )
        for value in transfer_values
    )


def visibility_candidates(
    *,
    half_life_days: float,
    damage_transfer_fraction: float,
    visibility_values: tuple[float, ...],
) -> tuple[Stage9DelayedCandidate, ...]:
    return tuple(
        Stage9DelayedCandidate(
            candidate_id=_id(
                transfer=damage_transfer_fraction,
                half_life_days=half_life_days,
                visibility=value,
            ),
            damage_transfer_fraction=damage_transfer_fraction,
            damage_half_life_days=half_life_days,
            damaged_visibility=value,
            complexity_rank=3,
        )
        for value in visibility_values
    )


def deduplicate_candidates(
    candidates: tuple[Stage9DelayedCandidate, ...],
) -> tuple[Stage9DelayedCandidate, ...]:
    by_id: dict[str, Stage9DelayedCandidate] = {}
    for candidate in candidates:
        existing = by_id.get(candidate.candidate_id)
        if existing is not None and existing != candidate:
            raise ValueError(
                f"Candidate ID collision: {candidate.candidate_id}"
            )
        by_id[candidate.candidate_id] = candidate

    return tuple(
        by_id[candidate_id]
        for candidate_id in sorted(by_id)
    )
