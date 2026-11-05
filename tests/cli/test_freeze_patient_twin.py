from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import gbm_twin.cli.freeze_patient_twin as cli_module
from gbm_twin.workflows.eligibility import (
    EligibilityIssue,
    EligibilityReason,
    PatientEligibility,
)
from gbm_twin.workflows.patient_twin import (
    PatientNotEligibleError,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)


def make_artifact(
    directory: Path,
) -> FrozenV2PredictionArtifact:
    field = np.zeros(
        (2, 2, 2),
        dtype=np.float32,
    )

    mask = np.zeros(
        (2, 2, 2),
        dtype=bool,
    )

    return FrozenV2PredictionArtifact(
        directory=directory,
        manifest={
            "sealed": True,
        },
        prediction_field=field,
        prediction_mask=mask,
        persistence_mask=mask.copy(),
        volume_baseline_mask=(
            mask.copy()
        ),
    )


def test_cli_uses_patient_specific_defaults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected_output = (
        tmp_path
        / "results"
        / "twin"
        / "patient-42"
        / "frozen-v2"
    )

    def fake_freeze(
        *,
        patient_id: int,
        experiment_config_path: Path,
        dataset_manifest_path: Path,
        repo_root: Path,
        cache_dir: Path,
        output_dir: Path,
        workers: int = 1,
    ) -> FrozenV2PredictionArtifact:
        assert patient_id == 42

        assert repo_root == (
            tmp_path.resolve()
        )

        assert (
            experiment_config_path
            == tmp_path.resolve()
            / "configs"
            / "experiments"
            / "mini_cohort.yaml"
        )

        assert (
            dataset_manifest_path
            == tmp_path.resolve()
            / "configs"
            / "datasets"
            / "cfb_gbm_v4.yaml"
        )

        assert cache_dir == (
            tmp_path.resolve()
            / "results"
            / "cache"
            / "v2"
            / "patient-42"
        )

        assert (
            output_dir
            == expected_output.resolve()
        )

        assert workers == 3

        return make_artifact(
            output_dir
        )

    monkeypatch.setattr(
        cli_module,
        "freeze_patient_from_configs",
        fake_freeze,
    )

    exit_code = cli_module.main(
        [
            "42",
            "--repo-root",
            str(tmp_path),
            "--workers",
            "3",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0

    assert (
        "Frozen V2 prediction created"
        in captured.out
    )

    assert captured.err == ""


def test_cli_accepts_explicit_output_and_cache_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    custom_cache = Path(
        "custom-cache"
    )

    custom_output = Path(
        "custom-output"
    )

    def fake_freeze(
        *,
        patient_id: int,
        experiment_config_path: Path,
        dataset_manifest_path: Path,
        repo_root: Path,
        cache_dir: Path,
        output_dir: Path,
        workers: int = 1,
    ) -> FrozenV2PredictionArtifact:
        assert patient_id == 108

        assert cache_dir == (
            tmp_path.resolve()
            / custom_cache
        )

        assert output_dir == (
            tmp_path.resolve()
            / custom_output
        )

        return make_artifact(
            output_dir
        )

    monkeypatch.setattr(
        cli_module,
        "freeze_patient_from_configs",
        fake_freeze,
    )

    exit_code = cli_module.main(
        [
            "108",
            "--repo-root",
            str(tmp_path),
            "--cache-dir",
            str(custom_cache),
            "--output-dir",
            str(custom_output),
        ]
    )

    assert exit_code == 0


def test_cli_reports_ineligible_patient(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    eligibility = PatientEligibility(
        patient_id=42,
        issues=(
            EligibilityIssue(
                reason=(
                    EligibilityReason
                    .TREATMENT_SCHEDULE_UNAVAILABLE
                ),
                detail=(
                    "treatment record "
                    "is missing"
                ),
            ),
        ),
    )

    def fake_freeze(
        *,
        patient_id: int,
        experiment_config_path: Path,
        dataset_manifest_path: Path,
        repo_root: Path,
        cache_dir: Path,
        output_dir: Path,
        workers: int = 1,
    ) -> FrozenV2PredictionArtifact:
        raise PatientNotEligibleError(
            eligibility
        )

    monkeypatch.setattr(
        cli_module,
        "freeze_patient_from_configs",
        fake_freeze,
    )

    exit_code = cli_module.main(
        [
            "42",
            "--repo-root",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 2
    assert captured.out == ""

    assert (
        "treatment_schedule_unavailable"
        in captured.err
    )

    assert (
        "treatment record is missing"
        in captured.err
    )


def test_cli_rejects_zero_workers() -> None:
    with pytest.raises(
        SystemExit,
    ) as exc_info:
        cli_module.main(
            [
                "42",
                "--workers",
                "0",
            ]
        )

    assert exc_info.value.code == 2