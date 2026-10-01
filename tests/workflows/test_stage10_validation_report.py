from gbm_twin.workflows.stage10_validation_report import (
    render_stage10_validation_markdown,
)


def _manifest(
    decision: str,
) -> dict[str, object]:
    return {
        "sealed": True,
        "decision": decision,
        "frozen_model": {
            "model_id": (
                "stage10-decoupled-half-life-60d"
            ),
        },
        "summary": {
            "patient_count": 16,
            "mean_twin_dice": 0.72,
            "mean_persistence_dice": 0.70,
            "mean_delta_vs_persistence": 0.02,
            "median_delta_vs_persistence": 0.01,
            "bootstrap_mean_delta_ci95": [
                -0.01,
                0.05,
            ],
            "catastrophic_failure_count": 0,
            "mean_twin_relative_volume_error": 0.8,
            "mean_persistence_relative_volume_error": 0.9,
            "mean_twin_hd95_mm": 9.0,
            "mean_persistence_hd95_mm": 10.0,
        },
        "leakage_control": {
            "reserve_validation_patient_ids": (
                list(
                    range(
                        16
                    )
                )
            ),
            "remaining_reserve_patient_ids": (
                list(
                    range(
                        32
                    )
                )
            ),
        },
        "failed_guardrails": (
            []
            if decision
            == "validation_passed"
            else [
                "mean_delta_vs_persistence",
            ]
        ),
        "next_step": (
            "holdout"
            if decision
            == "validation_passed"
            else "failure-analysis"
        ),
    }


def test_stage10_validation_report_shows_passed_next_step(
) -> None:
    text = (
        render_stage10_validation_markdown(
            _manifest(
                "validation_passed"
            )
        )
    )

    assert (
        "All pre-specified guardrails passed."
        in text
    )

    assert "holdout" in text


def test_stage10_validation_report_shows_failed_guardrails(
) -> None:
    text = (
        render_stage10_validation_markdown(
            _manifest(
                "validation_failed"
            )
        )
    )

    assert (
        "mean_delta_vs_persistence"
        in text
    )

    assert (
        "Do not tune on the revealed"
        in text
    )
