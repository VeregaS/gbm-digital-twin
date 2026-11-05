from __future__ import annotations

from gbm_twin.workflows.stage9_protocol import (
    Stage9DelayedResponseConfig,
    Stage9ProtocolConfig,
    Stage9SelectionConfig,
)
from gbm_twin.workflows.stage9_selection import (
    Stage9CandidateSummary,
    _select_summary,
)


def _config() -> Stage9ProtocolConfig:
    return Stage9ProtocolConfig(
        schema_version=1,
        design="frozen_stage8_kinetics_delayed_response_v1",
        delayed=Stage9DelayedResponseConfig(
            half_life_days=(14.0, 30.0, 60.0),
            transfer_fractions=(0.5, 0.75, 1.0),
            visibility_values=(0.5, 0.75, 1.0),
        ),
        selection=Stage9SelectionConfig(
            catastrophic_delta_vs_persistence=-0.10,
            min_mean_dice_gain_over_stage8_control=0.005,
            max_additional_catastrophic_failures=0,
        ),
    )


def _summary(
    candidate_id: str,
    *,
    mean_dice: float,
    median_dice: float,
    catastrophic: int,
) -> Stage9CandidateSummary:
    return Stage9CandidateSummary(
        candidate_id=candidate_id,
        complexity_rank=0 if candidate_id == "control" else 1,
        patient_count=10,
        mean_dice=mean_dice,
        median_dice=median_dice,
        mean_delta_vs_persistence=mean_dice - 0.70,
        median_delta_vs_persistence=median_dice - 0.70,
        mean_relative_volume_error=0.2,
        mean_hd95_mm=5.0,
        catastrophic_failure_count=catastrophic,
        better_count=5,
        equal_count=0,
        worse_count=5,
    )


def test_stage9_selection_rejects_tiny_mean_gain() -> None:
    control = _summary(
        "control",
        mean_dice=0.70,
        median_dice=0.70,
        catastrophic=1,
    )
    candidate = _summary(
        "delayed",
        mean_dice=0.703,
        median_dice=0.72,
        catastrophic=0,
    )

    selected = _select_summary(
        (control, candidate),
        control=control,
        config=_config(),
    )

    assert selected.candidate_id == "control"


def test_stage9_selection_rejects_new_catastrophic_failure() -> None:
    control = _summary(
        "control",
        mean_dice=0.70,
        median_dice=0.70,
        catastrophic=1,
    )
    candidate = _summary(
        "delayed",
        mean_dice=0.73,
        median_dice=0.73,
        catastrophic=2,
    )

    selected = _select_summary(
        (control, candidate),
        control=control,
        config=_config(),
    )

    assert selected.candidate_id == "control"


def test_stage9_selection_accepts_material_safe_gain() -> None:
    control = _summary(
        "control",
        mean_dice=0.70,
        median_dice=0.70,
        catastrophic=1,
    )
    candidate = _summary(
        "delayed",
        mean_dice=0.72,
        median_dice=0.71,
        catastrophic=1,
    )

    selected = _select_summary(
        (control, candidate),
        control=control,
        config=_config(),
    )

    assert selected.candidate_id == "delayed"
