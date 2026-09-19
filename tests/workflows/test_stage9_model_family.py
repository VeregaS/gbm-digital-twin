from __future__ import annotations

from gbm_twin.workflows.stage9_model_family import (
    control_candidate,
    deduplicate_candidates,
    timescale_candidates,
    transfer_candidates,
    visibility_candidates,
)


def test_stage9_family_reuses_identical_candidate_identity() -> None:
    timescale = timescale_candidates((14.0, 30.0, 60.0))
    transfer = transfer_candidates(
        half_life_days=30.0,
        transfer_values=(0.5, 0.75, 1.0),
    )
    visibility = visibility_candidates(
        half_life_days=30.0,
        damage_transfer_fraction=1.0,
        visibility_values=(0.5, 0.75, 1.0),
    )

    combined = deduplicate_candidates(
        (control_candidate(), *timescale, *transfer, *visibility)
    )
    ids = [candidate.candidate_id for candidate in combined]

    assert len(ids) == len(set(ids))
    candidate = next(
        item
        for item in combined
        if item.candidate_id
        == "stage9-delayed-transfer-1-half-life-30d-visibility-1"
    )
    assert candidate.complexity_rank == 1


def test_stage9_control_has_no_delayed_transfer() -> None:
    control = control_candidate()

    assert control.damage_transfer_fraction == 0.0
    assert control.complexity_rank == 0
