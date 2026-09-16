from __future__ import annotations

from pathlib import Path

import pytest

import gbm_twin.cli.freeze_cohort as cli_module
from gbm_twin.workflows.cohort_freeze import (
    CohortFreezeManifestPayload,
    CohortFreezeResult,
)


def make_result(
    directory: Path,
) -> CohortFreezeResult:
    manifest: (
        CohortFreezeManifestPayload
    ) = {
        "schema_version": 1,
        "kind": "v2_cohort_freeze",
        "frozen": True,
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": "10.7937/v9pn-2f72",
        },
        "repository": {
            "commit_sha": (
                "0123456789abcdef"
                "0123456789abcdef"
                "01234567"
            ),
            "dirty": False,
        },
        "experiment": {
            "experiment_config_file": (
                "mini_cohort.yaml"
            ),
            "dataset_manifest_file": (
                "cfb_gbm_v4.yaml"
            ),
            "calibration_config_sha256": (
                "a" * 64
            ),
            "target_spacing": [
                2.0,
                2.0,
                2.0,
            ],
            "selected_patient_ids": [
                42,
                108,
            ],
        },
        "frozen_patients": [
            {
                "patient_id": 42,
                "artifact_dir": (
                    "patients/"
                    "patient-42/"
                    "frozen-v2"
                ),
            },
        ],
        "excluded_patients": [
            {
                "patient_id": 108,
                "issues": [
                    {
                        "reason": (
                            "treatment_schedule_"
                            "unavailable"
                        ),
                        "detail": (
                            "Treatment schedule "
                            "is unavailable"
                        ),
                    },
                ],
            },
        ],
    }

    return CohortFreezeResult(
        directory=directory,
        manifest=manifest,
    )


def test_cli_uses_default_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path.resolve()

    expected_cache = (
        repo_root
        / "results"
        / "cache"
        / "v2-cohort"
    )

    expected_output = (
        repo_root
        / "results"
        / "cohort"
        / "v2-freeze"
    )

    def fake_freeze(
        *,
        experiment_config_path: Path,
        dataset_manifest_path: Path,
        repo_root: Path,
        cache_root: Path,
        output_root: Path,
        workers: int = 1,
        allow_dirty: bool = False,
    ) -> CohortFreezeResult:
        assert (
            repo_root
            == tmp_path.resolve()
        )

        assert (
            experiment_config_path
            == repo_root
            / "configs"
            / "experiments"
            / "mini_cohort.yaml"
        )

        assert (
            dataset_manifest_path
            == repo_root
            / "configs"
            / "datasets"
            / "cfb_gbm_v4.yaml"
        )

        assert (
            cache_root
            == expected_cache
        )

        assert (
            output_root
            == expected_output
        )

        assert workers == 3
        assert not allow_dirty

        return make_result(
            output_root
        )

    monkeypatch.setattr(
        cli_module,
        "freeze_cohort_from_configs",
        fake_freeze,
    )

    exit_code = cli_module.main(
        [
            "--repo-root",
            str(tmp_path),
            "--workers",
            "3",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""

    assert (
        "Cohort V2 freeze created"
        in captured.out
    )

    assert (
        "Frozen patients: 1"
        in captured.out
    )

    assert (
        "Excluded patients: 1"
        in captured.out
    )

    assert (
        "treatment_schedule_unavailable"
        in captured.out
    )


def test_cli_passes_explicit_paths_and_allow_dirty(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_freeze(
        *,
        experiment_config_path: Path,
        dataset_manifest_path: Path,
        repo_root: Path,
        cache_root: Path,
        output_root: Path,
        workers: int = 1,
        allow_dirty: bool = False,
    ) -> CohortFreezeResult:
        assert (
            cache_root
            == tmp_path.resolve()
            / "custom-cache"
        )

        assert (
            output_root
            == tmp_path.resolve()
            / "custom-freeze"
        )

        assert allow_dirty
        assert workers == 2

        return make_result(
            output_root
        )

    monkeypatch.setattr(
        cli_module,
        "freeze_cohort_from_configs",
        fake_freeze,
    )

    exit_code = cli_module.main(
        [
            "--repo-root",
            str(tmp_path),
            "--cache-root",
            "custom-cache",
            "--output-root",
            "custom-freeze",
            "--workers",
            "2",
            "--allow-dirty",
        ]
    )

    assert exit_code == 0


def test_cli_reports_workflow_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_freeze(
        *,
        experiment_config_path: Path,
        dataset_manifest_path: Path,
        repo_root: Path,
        cache_root: Path,
        output_root: Path,
        workers: int = 1,
        allow_dirty: bool = False,
    ) -> CohortFreezeResult:
        raise ValueError(
            "Cohort freeze requires a "
            "clean Git working tree"
        )

    monkeypatch.setattr(
        cli_module,
        "freeze_cohort_from_configs",
        fake_freeze,
    )

    exit_code = cli_module.main(
        [
            "--repo-root",
            str(tmp_path),
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""

    assert (
        "clean Git working tree"
        in captured.err
    )


def test_cli_rejects_zero_workers() -> None:
    with pytest.raises(
        SystemExit,
    ) as exc_info:
        cli_module.main(
            [
                "--workers",
                "0",
            ]
        )

    assert exc_info.value.code == 2