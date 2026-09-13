import pytest

from gbm_twin.models.treatment import (
    TreatmentWindow,
)


def test_treatment_is_inactive_before_start() -> None:
    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=30.0,
        kill_rate=0.05,
    )

    assert (
        treatment.kill_rate_at(5.0)
        == 0.0
    )


def test_treatment_is_active_inside_window() -> None:
    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=30.0,
        kill_rate=0.05,
    )

    assert (
        treatment.kill_rate_at(20.0)
        == 0.05
    )


def test_treatment_is_inactive_after_end() -> None:
    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=30.0,
        kill_rate=0.05,
    )

    assert (
        treatment.kill_rate_at(30.0)
        == 0.0
    )


def test_treatment_start_is_inclusive() -> None:
    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=30.0,
        kill_rate=0.05,
    )

    assert (
        treatment.kill_rate_at(10.0)
        == 0.05
    )


def test_rejects_negative_start_day() -> None:
    with pytest.raises(
        ValueError,
        match="start day",
    ):
        TreatmentWindow(
            start_day=-1.0,
            end_day=30.0,
            kill_rate=0.05,
        )


def test_rejects_invalid_end_day() -> None:
    with pytest.raises(
        ValueError,
        match="end day",
    ):
        TreatmentWindow(
            start_day=10.0,
            end_day=10.0,
            kill_rate=0.05,
        )


def test_rejects_negative_kill_rate() -> None:
    with pytest.raises(
        ValueError,
        match="kill rate",
    ):
        TreatmentWindow(
            start_day=10.0,
            end_day=30.0,
            kill_rate=-0.05,
        )


def test_rejects_negative_simulation_time() -> None:
    treatment = TreatmentWindow(
        start_day=10.0,
        end_day=30.0,
        kill_rate=0.05,
    )

    with pytest.raises(
        ValueError,
        match="Simulation time",
    ):
        treatment.kill_rate_at(-1.0)