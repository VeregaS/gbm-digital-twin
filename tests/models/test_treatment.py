import math

import pytest

from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
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


def test_fractionated_rt_total_dose() -> None:
    treatment = FractionatedRadiotherapy(
        fraction_days=(
            10.0,
            11.0,
            12.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    assert treatment.fractions_number == 3

    assert treatment.total_dose_gy == pytest.approx(
        6.0
    )


def test_fractionated_rt_survival_fraction() -> None:
    treatment = FractionatedRadiotherapy(
        fraction_days=(
            10.0,
            11.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    expected = math.exp(
        -(
            0.1 * 2.0
            + 0.02 * 2.0**2
        )
    )

    assert (
        treatment.survival_fraction_per_fraction
        == pytest.approx(expected)
    )


def test_fractionated_rt_detects_fraction_day() -> None:
    treatment = FractionatedRadiotherapy(
        fraction_days=(
            10.0,
            12.0,
            14.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    assert treatment.has_fraction_at(
        12.0
    )

    assert not treatment.has_fraction_at(
        13.0
    )


def test_fractionated_rt_survival_only_on_fraction_day() -> None:
    treatment = FractionatedRadiotherapy(
        fraction_days=(
            10.0,
            12.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.02,
    )

    assert (
        treatment.survival_fraction_at(9.0)
        == 1.0
    )

    assert (
        treatment.survival_fraction_at(10.0)
        < 1.0
    )

    assert (
        treatment.survival_fraction_at(11.0)
        == 1.0
    )


def test_fractionated_rt_rejects_empty_schedule() -> None:
    with pytest.raises(
        ValueError,
        match="At least one",
    ):
        FractionatedRadiotherapy(
            fraction_days=(),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.02,
        )


def test_fractionated_rt_rejects_negative_fraction_day() -> None:
    with pytest.raises(
        ValueError,
        match="Fraction days",
    ):
        FractionatedRadiotherapy(
            fraction_days=(
                -1.0,
                1.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.02,
        )


def test_fractionated_rt_rejects_duplicate_fraction_days() -> None:
    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        FractionatedRadiotherapy(
            fraction_days=(
                10.0,
                10.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.02,
        )


def test_fractionated_rt_rejects_unsorted_fraction_days() -> None:
    with pytest.raises(
        ValueError,
        match="strictly increasing",
    ):
        FractionatedRadiotherapy(
            fraction_days=(
                12.0,
                10.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.02,
        )


def test_fractionated_rt_rejects_nonpositive_dose() -> None:
    with pytest.raises(
        ValueError,
        match="Dose per fraction",
    ):
        FractionatedRadiotherapy(
            fraction_days=(
                10.0,
                11.0,
            ),
            dose_per_fraction_gy=0.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.02,
        )


def test_fractionated_rt_rejects_negative_alpha() -> None:
    with pytest.raises(
        ValueError,
        match="Alpha",
    ):
        FractionatedRadiotherapy(
            fraction_days=(
                10.0,
                11.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=-0.1,
            beta_per_gy2=0.02,
        )


def test_fractionated_rt_rejects_negative_beta() -> None:
    with pytest.raises(
        ValueError,
        match="Beta",
    ):
        FractionatedRadiotherapy(
            fraction_days=(
                10.0,
                11.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=-0.02,
        )