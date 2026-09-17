import pytest

from gbm_twin.workflows.treatment_timing import (
    derive_treatment_timing,
)


def test_treatment_timing_detects_rt_completed_before_t1() -> None:
    record = derive_treatment_timing(
        patient_id=42,
        t1_day=80.0,
        rt_start_day=10.0,
        total_dose_gy=60.0,
        fractions_number=30,
    )

    assert record.treatment_reconstructable is True
    assert record.last_fraction_day == pytest.approx(49.0)
    assert record.rt_completed_by_t1 is True
    assert record.fractions_after_t1 == 0
    assert (
        record.days_from_last_fraction_to_t1
        == pytest.approx(31.0)
    )


def test_treatment_timing_detects_future_fractions_after_t1() -> None:
    record = derive_treatment_timing(
        patient_id=42,
        t1_day=20.0,
        rt_start_day=10.0,
        total_dose_gy=60.0,
        fractions_number=30,
    )

    assert record.treatment_reconstructable is True
    assert record.last_fraction_day == pytest.approx(49.0)
    assert record.rt_completed_by_t1 is False
    assert record.fractions_after_t1 == 21
    assert (
        record.days_from_last_fraction_to_t1
        == pytest.approx(-29.0)
    )


def test_treatment_timing_handles_missing_schedule() -> None:
    record = derive_treatment_timing(
        patient_id=18,
        t1_day=80.0,
        rt_start_day=None,
        total_dose_gy=None,
        fractions_number=None,
    )

    assert record.treatment_reconstructable is False
    assert record.last_fraction_day is None
    assert record.rt_completed_by_t1 is None
    assert record.fractions_after_t1 is None
    assert record.days_from_last_fraction_to_t1 is None


def test_treatment_timing_handles_missing_t1_day() -> None:
    record = derive_treatment_timing(
        patient_id=42,
        t1_day=None,
        rt_start_day=10.0,
        total_dose_gy=60.0,
        fractions_number=30,
    )

    assert record.treatment_reconstructable is True
    assert record.last_fraction_day == pytest.approx(49.0)
    assert record.rt_completed_by_t1 is None
    assert record.fractions_after_t1 is None
    assert record.days_from_last_fraction_to_t1 is None
