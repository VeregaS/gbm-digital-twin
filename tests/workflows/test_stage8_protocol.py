from __future__ import annotations

from pathlib import Path

import pytest

from gbm_twin.workflows.stage8_protocol import load_stage8_protocol_config


def _write_config(path: Path, *, holdout_fraction: float = 0.25) -> None:
    path.write_text(
        f"""schema_version: 1
exposed_development_patient_ids: [8, 25]
holdout_fraction: {holdout_fraction}
split_seed: 42
required_timepoints: [t0, t1, t2]
required_modalities: [t1gd]
preferred_modalities: [flair, dwi]
require_complete_rt_schedule: true
require_rtdose: true
observation_model:
  enhancing_detection_threshold: 0.80
  infiltrative_detection_threshold: 0.16
  transition_width_mm: 4.0
chemotherapy:
  enabled: false
treatment_memory:
  enabled: true
  proliferation_survival_candidates: [1.0, 0.99]
""",
        encoding="utf-8",
    )


def test_load_stage8_protocol_config(tmp_path: Path) -> None:
    path = tmp_path / "stage8.yaml"
    _write_config(path)

    config = load_stage8_protocol_config(path)

    assert config.exposed_development_patient_ids == (8, 25)
    assert config.required_timepoints == ("t0", "t1", "t2")
    assert config.observation.enhancing_detection_threshold == pytest.approx(0.8)
    assert config.treatment_memory.proliferation_survival_candidates == (
        1.0,
        0.99,
    )
    assert config.chemotherapy_enabled is False


def test_stage8_protocol_rejects_invalid_holdout_fraction(tmp_path: Path) -> None:
    path = tmp_path / "stage8.yaml"
    _write_config(path, holdout_fraction=1.0)

    with pytest.raises(ValueError, match="holdout_fraction"):
        load_stage8_protocol_config(path)
