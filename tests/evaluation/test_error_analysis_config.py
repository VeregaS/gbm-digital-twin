from __future__ import annotations

from pathlib import Path

import pytest

from gbm_twin.evaluation.error_analysis_config import (
    load_cohort_error_analysis_config,
)


def test_load_cohort_error_analysis_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "analysis.yaml"

    path.write_text(
        "schema_version: 1\n"
        "stable_volume_change_fraction: 0.10\n"
        "worst_patient_count: 5\n"
        "min_correlation_patients: 3\n",
        encoding="utf-8",
    )

    config = load_cohort_error_analysis_config(
        path
    )

    assert config.stable_volume_change_fraction == pytest.approx(0.10)
    assert config.worst_patient_count == 5
    assert config.min_correlation_patients == 3


def test_error_analysis_config_rejects_invalid_correlation_count(
    tmp_path: Path,
) -> None:
    path = tmp_path / "analysis.yaml"

    path.write_text(
        "schema_version: 1\n"
        "stable_volume_change_fraction: 0.10\n"
        "worst_patient_count: 5\n"
        "min_correlation_patients: 1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="at least 2",
    ):
        load_cohort_error_analysis_config(
            path
        )


def test_error_analysis_config_rejects_unknown_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "analysis.yaml"

    path.write_text(
        "schema_version: 99\n"
        "stable_volume_change_fraction: 0.10\n"
        "worst_patient_count: 5\n"
        "min_correlation_patients: 3\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        load_cohort_error_analysis_config(
            path
        )
