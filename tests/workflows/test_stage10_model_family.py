from gbm_twin.workflows.stage9_model_family import (
    Stage9DelayedCandidate,
)
from gbm_twin.workflows.stage10_model_family import (
    build_stage10_candidates,
)


def test_stage10_family_contains_exact_control_and_fixed_diagnostic_grid(
) -> None:
    stage9 = Stage9DelayedCandidate(
        candidate_id=(
            "stage9-delayed-transfer-1-half-life-120d-visibility-1"
        ),
        damage_transfer_fraction=1.0,
        damage_half_life_days=120.0,
        damaged_visibility=1.0,
        complexity_rank=1,
    )

    candidates = (
        build_stage10_candidates(
            selected_stage9=stage9,
            half_life_days=(
                14.0,
                30.0,
                60.0,
            ),
        )
    )

    assert [
        item.kind
        for item in candidates
    ] == [
        "stage9-control",
        "decoupled",
        "decoupled",
        "decoupled",
    ]

    assert [
        item.damage_half_life_days
        for item in candidates
    ] == [
        120.0,
        14.0,
        30.0,
        60.0,
    ]


def test_stage10_rejects_nonselected_stage9_structure(
) -> None:
    stage9 = Stage9DelayedCandidate(
        candidate_id="bad",
        damage_transfer_fraction=0.5,
        damage_half_life_days=120.0,
        damaged_visibility=1.0,
        complexity_rank=2,
    )

    try:
        build_stage10_candidates(
            selected_stage9=stage9,
            half_life_days=(
                14.0,
            ),
        )
    except ValueError as exc:
        assert (
            "transfer=1"
            in str(
                exc
            )
        )
    else:
        raise AssertionError(
            "Stage 10 must reject an incompatible Stage 9 control"
        )
