from pathlib import Path

import pytest

from gbm_twin.workflows.stage10_model_family import (
    Stage10Candidate,
)
from gbm_twin.workflows.stage10_selection_artifact import (
    SelectedStage10Model,
)
from gbm_twin.workflows.stage10_validation_protocol import (
    load_frozen_stage10_model_config,
    load_stage10_validation_config,
    verify_frozen_stage10_model,
)


def _selected(
    sha256: str,
) -> SelectedStage10Model:
    return SelectedStage10Model(
        candidate=(
            Stage10Candidate(
                candidate_id=(
                    "stage10-decoupled-half-life-60d"
                ),
                kind="decoupled",
                damage_half_life_days=60.0,
                complexity_rank=2,
            )
        ),
        source_manifest_sha256=(
            sha256
        ),
        stage8_data_audit_sha256="a",
        stage8_model_selection_sha256="b",
        stage8_internal_validation_sha256="c",
        stage9_selection_sha256="d",
        reference_fidelity_v2_sha256="e",
        stage8_protocol_sha256="f",
        stage10_protocol_sha256="g",
        experiment_config_sha256="h",
        repository_commit_sha="i",
        reserve_patient_ids=(
            10,
            11,
        ),
        untouched_holdout_patient_ids=(
            99,
        ),
    )


def test_frozen_stage10_config_matches_selected_model(
    tmp_path: Path,
) -> None:
    config = (
        tmp_path
        / "frozen.yaml"
    )

    config.write_text(
        """
schema_version: 1
model_id: stage10-decoupled-half-life-60d
selection_artifact:
  sha256: abc
structure:
  kind: decoupled
  visible_damage_half_life_days: 60.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    loaded = (
        load_frozen_stage10_model_config(
            config
        )
    )

    assert (
        loaded
        .selection_artifact_sha256
        == "abc"
    )

    verified = (
        verify_frozen_stage10_model(
            selected=(
                _selected(
                    "abc"
                )
            ),
            config_path=(
                config
            ),
        )
    )

    assert (
        verified
        .visible_damage_half_life_days
        == 60.0
    )


@pytest.mark.parametrize("value", [".nan", ".inf", "-.inf"])
def test_frozen_config_rejects_nonfinite_half_life(tmp_path: Path, value: str) -> None:
    config = tmp_path / "frozen.yaml"
    config.write_text(
        "schema_version: 1\nmodel_id: test\nselection_artifact:\n  sha256: abc\n"
        "structure:\n  kind: decoupled\n  visible_damage_half_life_days: " + value + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="finite"):
        load_frozen_stage10_model_config(config)


def test_stage10_validation_config_loads_guardrails(
    tmp_path: Path,
) -> None:
    config = (
        tmp_path
        / "validation.yaml"
    )

    config.write_text(
        """
schema_version: 1
design: test
cohort:
  patient_count: 16
  seed: 42
  selection_method: deterministic_stratified_reserve_v1
evaluation:
  catastrophic_delta_vs_persistence: -0.10
  bootstrap_samples: 100
  bootstrap_seed: 43
advancement:
  min_mean_delta_vs_persistence: 0.0
  min_median_delta_vs_persistence: 0.0
  max_catastrophic_failure_count: 0
  require_mean_rve_not_worse_than_persistence: true
  require_mean_hd95_not_worse_than_persistence: true
next_step:
  if_passed: holdout
  if_failed: failure-analysis
""".strip()
        + "\n",
        encoding="utf-8",
    )

    loaded = (
        load_stage10_validation_config(
            config
        )
    )

    assert loaded.patient_count == 16
    assert loaded.seed == 42
    assert (
        loaded
        .max_catastrophic_failure_count
        == 0
    )
