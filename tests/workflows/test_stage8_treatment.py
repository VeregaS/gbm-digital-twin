from __future__ import annotations

import numpy as np
import pytest

from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.rt_schedule import reconstruct_weekday_like_schedule
from gbm_twin.workflows.stage8_treatment import (
    build_stage8_radiotherapy_events,
)


def test_uniform_stage8_events_preserve_schedule() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=10.0,
        total_dose_gy=6.0,
        fractions_number=3,
    )
    result = build_stage8_radiotherapy_events(
        schedule,
        RadiobiologyParameters(
            alpha_per_gy=0.12,
            alpha_beta_ratio_gy=10.0,
        ),
        proliferation_survival=0.99,
    )

    assert result.spatial_dose is False
    assert result.dose_normalization is None
    assert tuple(event.day for event in result.events) == (10.0, 11.0, 12.0)
    assert all(event.proliferation_survival == 0.99 for event in result.events)
    assert all(isinstance(event.immediate_survival, float) for event in result.events)


def test_spatial_stage8_events_build_lq_survival_field() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=0.0,
        total_dose_gy=60.0,
        fractions_number=30,
    )
    cumulative = np.full((3, 3, 3), 60.0, dtype=np.float32)
    cumulative[0, 0, 0] = 30.0

    result = build_stage8_radiotherapy_events(
        schedule,
        RadiobiologyParameters(
            alpha_per_gy=0.12,
            alpha_beta_ratio_gy=10.0,
        ),
        proliferation_survival=0.995,
        cumulative_rtdose=cumulative,
    )

    assert result.spatial_dose is True
    assert result.dose_normalization is not None
    assert result.dose_normalization.source_unit == "gy"
    assert len(result.events) == 30

    survival = result.events[0].immediate_survival
    assert isinstance(survival, np.ndarray)
    assert survival.shape == cumulative.shape
    assert survival[0, 0, 0] > survival[1, 1, 1]


def test_stage8_events_reject_invalid_proliferation_survival() -> None:
    schedule = reconstruct_weekday_like_schedule(
        start_day=0.0,
        total_dose_gy=2.0,
        fractions_number=1,
    )

    with pytest.raises(ValueError, match="proliferation_survival"):
        build_stage8_radiotherapy_events(
            schedule,
            RadiobiologyParameters(
                alpha_per_gy=0.12,
                alpha_beta_ratio_gy=10.0,
            ),
            proliferation_survival=0.0,
        )
