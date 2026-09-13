from pathlib import Path

from gbm_twin.evaluation.config import (
    evaluation_signature,
    load_cohort_experiment_config,
)


def test_load_cohort_experiment_config(
    tmp_path: Path,
) -> None:
    config_path = (
        tmp_path
        / "experiment.yaml"
    )

    config_path.write_text(
        """
patients:
  - 8
  - 18

data:
  metadata_root: "metadata"
  patients_root: "patients"

evaluation:
  target_spacing:
    - 2.0
    - 2.0
    - 2.0

  threshold: 0.5
  dt: 2.0

  diffusion_values:
    - 0.0
    - 0.005

  proliferation_values:
    - 0.0
    - 0.015

  volume_weight: 0.5

analysis:
  trajectory_stable_threshold: 0.10

output:
  raw_csv: "results/raw.csv"
  analyzed_csv: "results/analyzed.csv"
""",
        encoding="utf-8",
    )

    config = (
        load_cohort_experiment_config(
            config_path
        )
    )

    assert config.patient_ids == (
        8,
        18,
    )

    assert config.metadata_root == Path(
        "metadata"
    )

    assert config.patients_root == Path(
        "patients"
    )

    assert (
        config.evaluation.target_spacing
        == (2.0, 2.0, 2.0)
    )

    assert (
        config.evaluation.threshold
        == 0.5
    )

    assert config.evaluation.dt == 2.0

    assert (
        config.evaluation.diffusion_values
        == (
            0.0,
            0.005,
        )
    )

    assert (
        config.evaluation.proliferation_values
        == (
            0.0,
            0.015,
        )
    )

    assert (
        config.evaluation.volume_weight
        == 0.5
    )

    assert (
        config.trajectory_stable_threshold
        == 0.10
    )

    assert (
        config.raw_output_csv
        == Path("results/raw.csv")
    )

    assert (
        config.analyzed_output_csv
        == Path(
            "results/analyzed.csv"
        )
    )


def test_evaluation_signature_is_stable(
    tmp_path: Path,
) -> None:
    config_path = (
        tmp_path
        / "experiment.yaml"
    )

    config_path.write_text(
        """
patients:
  - 8

data:
  metadata_root: "metadata"
  patients_root: "patients"

evaluation:
  target_spacing:
    - 2.0
    - 2.0
    - 2.0

  threshold: 0.5
  dt: 2.0

  diffusion_values:
    - 0.0
    - 0.005

  proliferation_values:
    - 0.0
    - 0.015

  volume_weight: 0.5

analysis:
  trajectory_stable_threshold: 0.10

output:
  raw_csv: "results/raw.csv"
  analyzed_csv: "results/analyzed.csv"
""",
        encoding="utf-8",
    )

    experiment = (
        load_cohort_experiment_config(
            config_path
        )
    )

    first = evaluation_signature(
        experiment.evaluation
    )

    second = evaluation_signature(
        experiment.evaluation
    )

    assert first == second
    assert len(first) == 16