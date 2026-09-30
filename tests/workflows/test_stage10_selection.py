from gbm_twin.workflows.stage10_protocol import (
    Stage10ProtocolConfig,
    Stage10SelectionConfig,
)
from gbm_twin.workflows.stage10_selection import (
    Stage10CandidateSummary,
    select_stage10_summary,
)


def _summary(
    *,
    candidate_id: str,
    kind: str,
    catastrophic: int,
    mean_dice: float,
    regression_delta: float,
    growth_delta: float,
) -> Stage10CandidateSummary:
    return Stage10CandidateSummary(
        candidate_id=candidate_id,
        candidate_kind=kind,
        damage_half_life_days=(
            120.0
            if kind
            == "stage9-control"
            else 30.0
        ),
        complexity_rank=(
            1
            if kind
            == "stage9-control"
            else 2
        ),
        patient_count=24,
        mean_dice=mean_dice,
        median_dice=mean_dice,
        mean_delta_vs_persistence=-0.01,
        median_delta_vs_persistence=0.0,
        mean_relative_volume_error=0.9,
        mean_hd95_mm=11.0,
        catastrophic_failure_count=catastrophic,
        better_count=6,
        equal_count=10,
        worse_count=8,
        regression_patient_count=11,
        regression_mean_delta_vs_persistence=(
            regression_delta
        ),
        growth_patient_count=8,
        growth_mean_delta_vs_persistence=(
            growth_delta
        ),
        stable_patient_count=5,
        stable_mean_delta_vs_persistence=0.0,
    )


def _config(
) -> Stage10ProtocolConfig:
    return Stage10ProtocolConfig(
        schema_version=1,
        design=(
            "frozen_stage9_kinetics_decoupled_damage_v1"
        ),
        visible_damage_half_life_days=(
            14.0,
            30.0,
            60.0,
        ),
        selection=(
            Stage10SelectionConfig(
                catastrophic_delta_vs_persistence=-0.10,
                max_mean_dice_degradation=0.005,
                max_growth_delta_degradation=0.010,
                min_regression_delta_gain=0.0,
            )
        ),
    )


def test_stage10_candidate_advances_only_with_fewer_catastrophic_failures(
) -> None:
    control = _summary(
        candidate_id="control",
        kind="stage9-control",
        catastrophic=2,
        mean_dice=0.681,
        regression_delta=-0.029,
        growth_delta=0.006,
    )

    same_failures = _summary(
        candidate_id="same",
        kind="decoupled",
        catastrophic=2,
        mean_dice=0.690,
        regression_delta=-0.010,
        growth_delta=0.006,
    )

    improved = _summary(
        candidate_id="improved",
        kind="decoupled",
        catastrophic=1,
        mean_dice=0.680,
        regression_delta=-0.020,
        growth_delta=0.004,
    )

    selected = (
        select_stage10_summary(
            (
                control,
                same_failures,
                improved,
            ),
            control=control,
            config=_config(),
        )
    )

    assert (
        selected.candidate_id
        == "improved"
    )


def test_stage10_control_is_retained_when_regression_does_not_improve(
) -> None:
    control = _summary(
        candidate_id="control",
        kind="stage9-control",
        catastrophic=2,
        mean_dice=0.681,
        regression_delta=-0.029,
        growth_delta=0.006,
    )

    candidate = _summary(
        candidate_id="candidate",
        kind="decoupled",
        catastrophic=1,
        mean_dice=0.690,
        regression_delta=-0.040,
        growth_delta=0.010,
    )

    selected = (
        select_stage10_summary(
            (
                control,
                candidate,
            ),
            control=control,
            config=_config(),
        )
    )

    assert (
        selected.candidate_id
        == "control"
    )
