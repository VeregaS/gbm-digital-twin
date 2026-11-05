import json
from pathlib import Path

import numpy as np
import pytest

from gbm_twin.calibration.cache import (
    build_calibration_signature,
    candidate_cache_key,
    load_cached_metrics,
)
from gbm_twin.calibration.grid_search import grid_search
from gbm_twin.calibration.stage8 import Stage8CalibrationConfig, calibrate_stage8_interval
from gbm_twin.models.treatment_memory import initial_treatment_memory_state


@pytest.mark.parametrize(
    "payload",
    [
        [], {"cache_version": 1, "dice": float("nan"), "volume_error": 0.0},
        {"cache_version": 1, "dice": 0.5, "volume_error": float("inf")},
        {"cache_version": 1, "dice": 1.1, "volume_error": 0.0},
        {"cache_version": 1, "dice": 0.5, "volume_error": -1.0},
    ],
)
def test_legacy_cache_rejects_invalid_metrics(tmp_path: Path, payload: object) -> None:
    path = tmp_path / "ab" / "abcdef.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert load_cached_metrics(tmp_path, "abcdef") is None


def test_stage8_exact_tie_is_stable_when_best_entry_is_missing(tmp_path: Path) -> None:
    field = np.full((3, 3, 3), 0.9, dtype=np.float32)
    domain = np.ones_like(field, dtype=bool)
    kwargs = dict(
        initial_state=initial_treatment_memory_state(field),
        observed_mask=domain, domain_mask=domain, spacing=(2.0, 2.0, 2.0),
        duration_days=1.0, fraction_events=(),
        config=Stage8CalibrationConfig(
            diffusion_values=(0.0, 0.01), proliferation_values=(0.0, 0.01),
            dt_days=0.5, observation_threshold=0.8, refinement_rounds=1,
        ),
        cache_dir=tmp_path, workers=1,
    )
    first = calibrate_stage8_interval(**kwargs)
    assert sum(result.loss == first.best.loss for result in first.candidates) > 1
    for entry in (tmp_path / first.cache_signature).glob("*.json"):
        payload = json.loads(entry.read_text(encoding="utf-8"))
        if (payload["diffusion"], payload["proliferation"]) == (
            first.best.diffusion, first.best.proliferation,
        ):
            entry.unlink()
    second = calibrate_stage8_interval(**kwargs)
    assert second.best == first.best
    assert second.candidates == first.candidates


def test_legacy_exact_tie_is_stable_after_partial_cache_resume(tmp_path: Path) -> None:
    field = np.full((3, 3, 3), 0.9, dtype=np.float32)
    domain = np.ones_like(field, dtype=bool)
    kwargs = dict(
        initial_field=field, observed_mask=domain, domain_mask=domain,
        spacing=(2.0, 2.0, 2.0), duration_days=1.0, dt=0.5,
        diffusion_values=[0.0, 0.01], proliferation_values=[0.0, 0.01],
        threshold=0.8, volume_weight=0.5, cache_dir=tmp_path,
    )
    first = grid_search(**kwargs)
    assert sum(result.loss == first[0].loss for result in first) > 1
    signature = build_calibration_signature(
        initial_field=field, observed_mask=domain, domain_mask=domain,
        spacing=(2.0, 2.0, 2.0), duration_days=1.0, dt=0.5,
        threshold=0.8, treatment=None, start_time_day=0.0,
    )
    key = candidate_cache_key(
        signature, diffusion=first[0].diffusion, proliferation=first[0].proliferation,
    )
    (tmp_path / key[:2] / (key + ".json")).unlink()
    second = grid_search(**kwargs)
    assert second == first


@pytest.mark.parametrize("key", ["dice", "volume_error", "loss"])
def test_stage8_recomputes_nonfinite_cache_entry(tmp_path: Path, key: str) -> None:
    field = np.full((3, 3, 3), 0.9, dtype=np.float32)
    domain = np.ones_like(field, dtype=bool)
    kwargs = dict(
        initial_state=initial_treatment_memory_state(field),
        observed_mask=domain, domain_mask=domain, spacing=(2.0, 2.0, 2.0),
        duration_days=1.0, fraction_events=(),
        config=Stage8CalibrationConfig(
            diffusion_values=(0.0, 0.01), proliferation_values=(0.0, 0.01),
            dt_days=0.5, observation_threshold=0.8, refinement_rounds=1,
        ),
        cache_dir=tmp_path, workers=1,
    )
    first = calibrate_stage8_interval(**kwargs)
    entries = list((tmp_path / first.cache_signature).glob("*.json"))
    assert entries
    for entry in entries:
        payload = json.loads(entry.read_text(encoding="utf-8"))
        payload[key] = float("nan")
        entry.write_text(json.dumps(payload), encoding="utf-8")
    second = calibrate_stage8_interval(**kwargs)
    assert second.best == first.best
    for entry in entries:
        repaired = json.loads(entry.read_text(encoding="utf-8"))
        assert np.isfinite(repaired[key])
