from __future__ import annotations

from pathlib import Path

import numpy as np

from gbm_twin.calibration.stage8 import (
    Stage8CalibrationConfig,
    calibrate_stage8_interval,
)
from gbm_twin.models.treatment_memory import initial_treatment_memory_state


def _config() -> Stage8CalibrationConfig:
    return Stage8CalibrationConfig(
        diffusion_values=(0.0, 0.01),
        proliferation_values=(0.0, 0.01),
        dt_days=0.5,
        observation_threshold=0.8,
        refinement_rounds=1,
    )


def test_stage8_calibration_fits_simple_static_observation(
    tmp_path: Path,
) -> None:
    field = np.zeros((5, 5, 5), dtype=np.float32)
    field[2, 2, 2] = 0.95
    domain = np.ones_like(field, dtype=bool)
    observed = field >= 0.8
    state = initial_treatment_memory_state(field, domain_mask=domain)

    result = calibrate_stage8_interval(
        initial_state=state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        fraction_events=(),
        config=_config(),
        cache_dir=tmp_path / "cache",
        workers=1,
    )

    assert result.best.diffusion >= 0.0
    assert result.best.proliferation >= 0.0
    assert 0.0 <= result.best.dice <= 1.0
    assert result.candidates
    assert len(result.cache_signature) == 64

    repeated = calibrate_stage8_interval(
        initial_state=state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        fraction_events=(),
        config=_config(),
        cache_dir=tmp_path / "cache",
        workers=1,
    )

    assert repeated.best == result.best
    assert repeated.cache_signature == result.cache_signature


def test_stage8_calibration_cache_signature_includes_absolute_start_day(
    tmp_path: Path,
) -> None:
    field = np.zeros((5, 5, 5), dtype=np.float32)
    field[2, 2, 2] = 0.95
    domain = np.ones_like(field, dtype=bool)
    observed = field >= 0.8
    state = initial_treatment_memory_state(field, domain_mask=domain)

    first = calibrate_stage8_interval(
        initial_state=state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        start_time_day=0.0,
        fraction_events=(),
        config=_config(),
        cache_dir=tmp_path / "cache",
        workers=1,
    )
    shifted = calibrate_stage8_interval(
        initial_state=state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        start_time_day=10.0,
        fraction_events=(),
        config=_config(),
        cache_dir=tmp_path / "cache",
        workers=1,
    )

    assert first.cache_signature != shifted.cache_signature


def test_stage8_calibration_progress_and_corrupt_cache_recovery(
    tmp_path: Path,
) -> None:
    field = np.zeros((5, 5, 5), dtype=np.float32)
    field[2, 2, 2] = 0.95
    domain = np.ones_like(field, dtype=bool)
    observed = field >= 0.8
    state = initial_treatment_memory_state(field, domain_mask=domain)
    cache_root = tmp_path / "cache"
    first_progress: list[str] = []

    first = calibrate_stage8_interval(
        initial_state=state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        fraction_events=(),
        config=_config(),
        cache_dir=cache_root,
        workers=1,
        progress=first_progress.append,
    )

    assert any("coarse:" in message for message in first_progress)
    assert any("refinement 1/1:" in message for message in first_progress)

    cache_files = sorted(
        (cache_root / first.cache_signature).glob("*.json")
    )
    assert cache_files

    cache_files[0].write_text("{broken", encoding="utf-8")
    second_progress: list[str] = []

    recovered = calibrate_stage8_interval(
        initial_state=state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        fraction_events=(),
        config=_config(),
        cache_dir=cache_root,
        workers=1,
        progress=second_progress.append,
    )

    assert recovered.best == first.best
    assert any("to compute" in message for message in second_progress)
