from __future__ import annotations

from pathlib import Path

import pytest

from gbm_twin.evaluation.config import (
    evaluation_signature,
    load_cohort_experiment_config,
)


def _write_config(
    path: Path,
    *,
    refinement_rounds: int | None = None,
    expansion_factor: float | None = None,
) -> None:
    refinement_lines = ""

    if refinement_rounds is not None:
        refinement_lines += (
            f"  refinement_rounds: {refinement_rounds}\n"
        )

    if expansion_factor is not None:
        refinement_lines += (
            "  upper_boundary_expansion_factor: "
            f"{expansion_factor}\n"
        )

    path.write_text(
        "patients:\n"
        "  - 8\n"
        "data:\n"
        "  metadata_root: \"metadata\"\n"
        "  patients_root: \"patients\"\n"
        "evaluation:\n"
        "  target_spacing:\n"
        "    - 2.0\n"
        "    - 2.0\n"
        "    - 2.0\n"
        "  threshold: 0.5\n"
        "  dt: 2.0\n"
        "  diffusion_values:\n"
        "    - 0.0\n"
        "    - 0.03\n"
        "  proliferation_values:\n"
        "    - 0.0\n"
        "    - 0.055\n"
        "  volume_weight: 0.5\n"
        f"{refinement_lines}"
        "analysis:\n"
        "  trajectory_stable_threshold: 0.10\n"
        "output:\n"
        "  raw_csv: \"results/raw.csv\"\n"
        "  analyzed_csv: \"results/analyzed.csv\"\n",
        encoding="utf-8",
    )


def test_refinement_settings_default_to_v2_behavior(
    tmp_path: Path,
) -> None:
    path = tmp_path / "baseline.yaml"
    _write_config(path)

    experiment = load_cohort_experiment_config(
        path
    )

    assert experiment.evaluation.refinement_rounds == 1
    assert (
        experiment.evaluation.upper_boundary_expansion_factor
        == pytest.approx(0.5)
    )


def test_refinement_settings_are_loaded_and_affect_signature(
    tmp_path: Path,
) -> None:
    baseline_path = tmp_path / "baseline.yaml"
    accuracy_path = tmp_path / "accuracy.yaml"

    _write_config(baseline_path)
    _write_config(
        accuracy_path,
        refinement_rounds=3,
        expansion_factor=1.0,
    )

    baseline = load_cohort_experiment_config(
        baseline_path
    )
    accuracy = load_cohort_experiment_config(
        accuracy_path
    )

    assert accuracy.evaluation.refinement_rounds == 3
    assert (
        accuracy.evaluation.upper_boundary_expansion_factor
        == pytest.approx(1.0)
    )

    assert (
        evaluation_signature(baseline.evaluation)
        != evaluation_signature(accuracy.evaluation)
    )


def test_refinement_settings_reject_invalid_values(
    tmp_path: Path,
) -> None:
    rounds_path = tmp_path / "invalid-rounds.yaml"
    factor_path = tmp_path / "invalid-factor.yaml"

    _write_config(
        rounds_path,
        refinement_rounds=0,
    )

    _write_config(
        factor_path,
        expansion_factor=0.0,
    )

    with pytest.raises(
        ValueError,
        match="refinement_rounds",
    ):
        load_cohort_experiment_config(
            rounds_path
        )

    with pytest.raises(
        ValueError,
        match="upper_boundary_expansion_factor",
    ):
        load_cohort_experiment_config(
            factor_path
        )
