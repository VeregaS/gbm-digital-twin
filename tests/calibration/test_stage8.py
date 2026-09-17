from __future__ import annotations

from pathlib import Path

import numpy as np

from gbm_twin.calibration.stage8 import (
    Stage8CalibrationConfig,
    calibrate_stage8_interval,
)
from gbm_twin.models.treatment_memory import initial_treatment_memory_state


def test_stage8_calibration_fits_simple_static_observation(
    tmp_path: Path,
) -> None:
    field = np.zeros((5, 5, 5), dtype=np.float32)
    field[2, 2, 2] = 0.95
    domain = np.ones_like(field, dtype=bool)
    observed = field >= 0.8

    result = calibrate_stage8_interval(
        initial_state=initial_treatment_memory_state(
            field,
            domain_mask=domain,
        ),
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        fraction_events=(),
        config=Stage8CalibrationConfig(
            diffusion_values=(0.0, 0.01),
            proliferation_values=(0.0, 0.01),
            dt_days=0.5,
            observation_threshold=0.8,
            refinement_rounds=1,
        ),
        cache_dir=tmp_path / "cache",
        workers=1,
    )

    assert result.best.diffusion >= 0.0
    assert result.best.proliferation >= 0.0
    assert 0.0 <= result.best.dice <= 1.0
    assert result.candidates
    assert len(result.cache_signature) == 64

    # A repeated run must be able to consume the persisted candidate cache.
    repeated = calibrate_stage8_interval(
        initial_state=initial_treatment_memory_state(
            field,
            domain_mask=domain,
        ),
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        fraction_events=(),
        config=Stage8CalibrationConfig(
            diffusion_values=(0.0, 0.01),
            proliferation_values=(0.0, 0.01),
            dt_days=0.5,
            observation_threshold=0.8,
            refinement_rounds=1,
        ),
        cache_dir=tmp_path / "cache",
        workers=1,
    )

    assert repeated.best == result.best
    assert repeated.cache_signature == result.cache_signature
