from pathlib import Path

from gbm_twin.evaluation.config import (
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
    - 0.005
    - 0.015

  proliferation_values:
    - 0.015
    - 0.035

  volume_weight: 0.5

output:
  csv: "results/test.csv"
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
        == (0.005, 0.015)
    )

    assert (
        config.evaluation.proliferation_values
        == (0.015, 0.035)
    )

    assert (
        config.evaluation.volume_weight
        == 0.5
    )

    assert config.output_csv == Path(
        "results/test.csv"
    )