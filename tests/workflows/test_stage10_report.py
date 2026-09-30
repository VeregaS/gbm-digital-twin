from gbm_twin.workflows.stage10_report import (
    render_stage10_markdown,
)


def _summary(
    *,
    candidate_id: str,
    kind: str,
    mean_dice: float,
    catastrophic: int,
    regression: float,
    growth: float,
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "candidate_kind": kind,
        "damage_half_life_days": 30.0,
        "complexity_rank": 1,
        "patient_count": 24,
        "mean_dice": mean_dice,
        "median_dice": mean_dice,
        "mean_delta_vs_persistence": -0.01,
        "median_delta_vs_persistence": -0.01,
        "mean_relative_volume_error": 0.9,
        "mean_hd95_mm": 10.0,
        "catastrophic_failure_count": catastrophic,
        "better_count": 7,
        "equal_count": 0,
        "worse_count": 17,
        "regression_patient_count": 8,
        "regression_mean_delta_vs_persistence": regression,
        "growth_patient_count": 10,
        "growth_mean_delta_vs_persistence": growth,
        "stable_patient_count": 6,
        "stable_mean_delta_vs_persistence": -0.01,
    }


def test_report_routes_failed_stage10_to_observation_model(
) -> None:
    control = _summary(
        candidate_id="stage9-control",
        kind="stage9-control",
        mean_dice=0.6814,
        catastrophic=2,
        regression=-0.04,
        growth=0.01,
    )

    manifest = {
        "sealed": True,
        "decision": (
            "no_decoupled_candidate_advanced"
        ),
        "control_summary": control,
        "candidate_summaries": [
            control,
            _summary(
                candidate_id="stage10-30d",
                kind="decoupled",
                mean_dice=0.679,
                catastrophic=2,
                regression=-0.03,
                growth=0.01,
            ),
        ],
        "selected_summary": control,
    }

    text = render_stage10_markdown(
        manifest
    )

    assert (
        "MRI observation model"
        in text
    )

    assert (
        "Do not add further RT compartments"
        in text
    )


def test_report_routes_advanced_candidate_to_freeze(
) -> None:
    control = _summary(
        candidate_id="stage9-control",
        kind="stage9-control",
        mean_dice=0.6814,
        catastrophic=2,
        regression=-0.04,
        growth=0.01,
    )

    selected = _summary(
        candidate_id="stage10-30d",
        kind="decoupled",
        mean_dice=0.684,
        catastrophic=1,
        regression=-0.01,
        growth=0.01,
    )

    manifest = {
        "sealed": True,
        "decision": (
            "decoupled_candidate_advanced"
        ),
        "control_summary": control,
        "candidate_summaries": [
            control,
            selected,
        ],
        "selected_summary": selected,
    }

    text = render_stage10_markdown(
        manifest
    )

    assert (
        "Freeze the selected Stage 10 structure"
        in text
    )
