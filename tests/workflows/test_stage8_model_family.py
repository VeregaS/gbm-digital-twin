from __future__ import annotations

from pathlib import Path

from gbm_twin.workflows.stage8_model_family import (
    build_dose_candidates,
    build_final_alpha_sensitivity_candidates,
    build_memory_candidates,
    build_radiobiology_candidates,
)
from gbm_twin.workflows.stage8_protocol import load_stage8_protocol_config


def _protocol(tmp_path: Path):
    path = tmp_path / "stage8.yaml"
    path.write_text(
        """schema_version: 1
exposed_development_patient_ids: [1, 2, 3]
holdout_fraction: 0.25
split_seed: 7
required_timepoints: [t0, t1, t2]
required_modalities: [t1gd]
preferred_modalities: [flair, dwi]
require_complete_rt_schedule: true
require_rtdose: true
observation_model:
  enhancing_detection_threshold: 0.80
  infiltrative_detection_threshold: 0.16
  transition_width_mm: 4.0
radiobiology:
  alpha_beta_ratio_gy: 10.0
  legacy_alpha_per_gy: 0.01
  reference_alpha_per_gy: 0.12
  effective_alpha_candidates_per_gy: [0.01, 0.10, 0.12, 0.14]
chemotherapy:
  enabled: false
treatment_memory:
  enabled: true
  proliferation_survival_candidates: [1.0, 0.995, 0.99, 0.98]
""",
        encoding="utf-8",
    )
    return load_stage8_protocol_config(path)


def test_nested_stage8_family_avoids_full_cartesian_search(
    tmp_path: Path,
) -> None:
    protocol = _protocol(tmp_path)

    radiobiology = build_radiobiology_candidates(protocol)
    assert len(radiobiology) == 4
    assert all(not candidate.use_spatial_rtdose for candidate in radiobiology)
    assert all(candidate.proliferation_survival == 1.0 for candidate in radiobiology)

    dose = build_dose_candidates(
        protocol,
        effective_alpha_per_gy=0.12,
    )
    assert len(dose) == 2
    assert {candidate.use_spatial_rtdose for candidate in dose} == {False, True}

    memory = build_memory_candidates(
        protocol,
        effective_alpha_per_gy=0.12,
        use_spatial_rtdose=True,
    )
    assert len(memory) == 4
    assert all(candidate.use_spatial_rtdose for candidate in memory)

    sensitivity = build_final_alpha_sensitivity_candidates(
        protocol,
        use_spatial_rtdose=True,
        proliferation_survival=0.99,
    )
    assert len(sensitivity) == 4
    assert {
        candidate.effective_alpha_per_gy
        for candidate in sensitivity
    } == {0.01, 0.10, 0.12, 0.14}

    # Across the sequential path, repeated candidates are cached/reused.
    unique_ids = {
        candidate.candidate_id
        for family in (radiobiology, dose, memory, sensitivity)
        for candidate in family
    }
    assert len(unique_ids) <= 11
    assert len(unique_ids) < 32
