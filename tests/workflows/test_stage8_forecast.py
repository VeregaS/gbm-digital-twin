from __future__ import annotations

from pathlib import Path

import numpy as np

from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.rt_schedule import reconstruct_weekday_like_schedule
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.stage8_forecast import simulate_stage8_forecast


def _volume(name: str, data: np.ndarray) -> NiftiVolume:
    return NiftiVolume(
        path=Path(name),
        data=data,
        affine=np.eye(4, dtype=np.float64),
        spacing=(1.0, 1.0, 1.0),
    )


def _timepoint(name: str, day: float) -> PreparedPatientTimepoint:
    shape = (7, 7, 7)
    brain = np.ones(shape, dtype=np.uint8)
    gtv = np.zeros(shape, dtype=np.uint8)
    gtv[2:5, 2:5, 2:5] = 1
    t1gd = np.zeros(shape, dtype=np.float32)

    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=_volume(f"{name}_t1gd.nii.gz", t1gd),
        gtv=_volume(f"{name}_gtv.nii.gz", gtv),
        brain_mask=_volume(f"{name}_brain.nii.gz", brain),
    )


def test_stage8_forecast_preserves_rt_memory_across_t1_assimilation() -> None:
    start = _timepoint("t0", 0.0)
    observed = _timepoint("t1", 2.0)
    schedule = reconstruct_weekday_like_schedule(
        start_day=0.0,
        total_dose_gy=2.0,
        fractions_number=1,
    )

    result = simulate_stage8_forecast(
        start=start,
        observed=observed,
        target_day=4.0,
        parameters=ReactionDiffusionParameters(
            diffusion=0.0,
            proliferation=0.0,
        ),
        schedule=schedule,
        radiobiology=RadiobiologyParameters(
            alpha_per_gy=0.12,
            alpha_beta_ratio_gy=10.0,
        ),
        proliferation_survival=0.9,
        dt_days=0.5,
        observation_parameters=MRIDetectionObservationParameters(),
    )

    inside = observed.gtv.data > 0.5

    assert np.allclose(
        result.pre_assimilation_state.proliferation_modifier[inside],
        0.9,
    )
    assert np.allclose(
        result.assimilated_state.proliferation_modifier[inside],
        0.9,
    )
    assert np.allclose(
        result.prediction_state.proliferation_modifier[inside],
        0.9,
    )
    assert result.prediction_mask.dtype == np.bool_
    assert np.any(result.prediction_mask)
