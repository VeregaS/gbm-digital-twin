import pytest

from gbm_twin.models.rt_schedule import (
    WEEKDAY_LIKE_ASSUMPTION,
    reconstruct_weekday_like_schedule,
)


def test_reconstruct_five_fraction_schedule() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=14.0,
        total_dose_gy=10.0,
        fractions_number=5,
    )

    assert schedule.fraction_days == (
        14.0,
        15.0,
        16.0,
        17.0,
        18.0,
    )

    assert (
        schedule.dose_per_fraction_gy
        == pytest.approx(2.0)
    )


def test_reconstruct_schedule_with_gap() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=14.0,
        total_dose_gy=20.0,
        fractions_number=10,
    )

    assert schedule.fraction_days == (
        14.0,
        15.0,
        16.0,
        17.0,
        18.0,
        21.0,
        22.0,
        23.0,
        24.0,
        25.0,
    )


def test_reconstruct_thirty_fraction_schedule() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=14.0,
        total_dose_gy=60.0,
        fractions_number=30,
    )

    assert schedule.fractions_number == 30

    assert (
        schedule.dose_per_fraction_gy
        == pytest.approx(2.0)
    )

    assert schedule.fraction_days[0] == 14.0

    assert schedule.fraction_days[-1] == 53.0


def test_reconstruct_fractional_dose() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=14.0,
        total_dose_gy=40.05,
        fractions_number=15,
    )

    assert (
        schedule.dose_per_fraction_gy
        == pytest.approx(2.67)
    )


def test_schedule_records_assumption() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=7.0,
        total_dose_gy=60.0,
        fractions_number=30,
    )

    assert (
        schedule.assumption
        == WEEKDAY_LIKE_ASSUMPTION
    )


def test_rejects_negative_start_day() -> None:
    with pytest.raises(
        ValueError,
        match="start day",
    ):
        reconstruct_weekday_like_schedule(
            start_day=-1.0,
            total_dose_gy=60.0,
            fractions_number=30,
        )


def test_rejects_nonpositive_total_dose() -> None:
    with pytest.raises(
        ValueError,
        match="dose",
    ):
        reconstruct_weekday_like_schedule(
            start_day=14.0,
            total_dose_gy=0.0,
            fractions_number=30,
        )


def test_rejects_nonpositive_fraction_count() -> None:
    with pytest.raises(
        ValueError,
        match="Fractions number",
    ):
        reconstruct_weekday_like_schedule(
            start_day=14.0,
            total_dose_gy=60.0,
            fractions_number=0,
        )