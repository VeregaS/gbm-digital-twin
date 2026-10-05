import pytest

from gbm_twin.workflows.stage10_validation import (
    evaluate_stage10_validation_summary,
)
from gbm_twin.workflows.stage10_validation_protocol import (
    Stage10ValidationConfig,
)


def _config(
) -> Stage10ValidationConfig:
    return Stage10ValidationConfig(
        schema_version=1,
        design="test",
        patient_count=16,
        seed=1,
        selection_method=(
            "deterministic_stratified_reserve_v1"
        ),
        catastrophic_delta_vs_persistence=-0.10,
        bootstrap_samples=100,
        bootstrap_seed=2,
        min_mean_delta_vs_persistence=0.0,
        min_median_delta_vs_persistence=0.0,
        max_catastrophic_failure_count=0,
        require_mean_rve_not_worse_than_persistence=True,
        require_mean_hd95_not_worse_than_persistence=True,
        next_step_if_passed="holdout",
        next_step_if_failed="failure-analysis",
    )


def _summary(
) -> dict[str, object]:
    return {
        "mean_delta_vs_persistence": 0.02,
        "median_delta_vs_persistence": 0.01,
        "catastrophic_failure_count": 0,
        "mean_twin_relative_volume_error": 0.8,
        "mean_persistence_relative_volume_error": 0.9,
        "mean_twin_hd95_mm": 9.0,
        "mean_persistence_hd95_mm": 10.0,
    }


def test_stage10_validation_passes_only_when_all_guardrails_pass(
) -> None:
    decision, failed = (
        evaluate_stage10_validation_summary(
            _summary(),
            _config(),
        )
    )

    assert decision == "validation_passed"
    assert failed == ()


@pytest.mark.parametrize("key", [
    "mean_delta_vs_persistence", "median_delta_vs_persistence",
    "mean_twin_relative_volume_error", "mean_persistence_relative_volume_error",
    "mean_twin_hd95_mm", "mean_persistence_hd95_mm",
])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_validation_never_passes_nonfinite_metrics(key: str, value: float) -> None:
    summary = _summary()
    summary[key] = value
    with pytest.raises(ValueError, match=key):
        evaluate_stage10_validation_summary(summary, _config())


@pytest.mark.parametrize("value", [-1, 0.5, True])
def test_validation_rejects_invalid_failure_counts(value: object) -> None:
    summary = _summary()
    summary["catastrophic_failure_count"] = value
    with pytest.raises(ValueError, match="catastrophic_failure_count"):
        evaluate_stage10_validation_summary(summary, _config())


def test_stage10_validation_fails_without_posthoc_ranking(
) -> None:
    summary = _summary()

    summary[
        "mean_delta_vs_persistence"
    ] = -0.001

    summary[
        "catastrophic_failure_count"
    ] = 1

    decision, failed = (
        evaluate_stage10_validation_summary(
            summary,
            _config(),
        )
    )

    assert decision == "validation_failed"

    assert set(
        failed
    ) == {
        "mean_delta_vs_persistence",
        "catastrophic_failure_count",
    }
