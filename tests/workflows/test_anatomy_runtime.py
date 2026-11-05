import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import gbm_twin.workflows.anatomy_runtime as anatomy_runtime
from gbm_twin.workflows.anatomy_runtime import (
    select_patient_atlas,
)


def _write_registration(
    directory: Path,
    *,
    status: str,
) -> None:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        directory
        / "registration.json"
    ).write_text(
        json.dumps(
            {
                "quality": {
                    "status": status,
                }
            }
        ),
        encoding="utf-8",
    )


def test_automatic_preview_uses_existing_candidate(
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    _write_registration(
        registration_dir,
        status="pass",
    )

    candidate = (
        registration_dir
        / "labels_candidate.nii.gz"
    )

    candidate.write_bytes(
        b"candidate"
    )

    selection = (
        select_patient_atlas(
            metadata_root=tmp_path,
            patients_root=tmp_path,
            atlas_root=tmp_path,
            patient_id=42,
            timepoint_name="t1",
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
        )
    )

    assert (
        selection.mode
        == "automatic-preview"
    )

    assert (
        selection.labelmap_path
        == candidate
    )

    assert (
        selection.automatic_qc_status
        == "pass"
    )


def test_manual_rejection_blocks_preview(
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    _write_registration(
        registration_dir,
        status="pass",
    )

    (
        registration_dir
        / "labels_candidate.nii.gz"
    ).write_bytes(
        b"candidate"
    )

    (
        registration_dir
        / "review.json"
    ).write_text(
        json.dumps(
            {
                "decision": "rejected",
            }
        ),
        encoding="utf-8",
    )

    selection = (
        select_patient_atlas(
            metadata_root=tmp_path,
            patients_root=tmp_path,
            atlas_root=tmp_path,
            patient_id=42,
            timepoint_name="t1",
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
        )
    )

    assert (
        selection.mode
        == "unavailable"
    )

    assert (
        selection.labelmap_path
        is None
    )



def test_read_only_selection_does_not_prepare_missing_registration(
    tmp_path: Path,
) -> None:
    selection = (
        select_patient_atlas(
            metadata_root=tmp_path,
            patients_root=tmp_path,
            atlas_root=tmp_path,
            patient_id=42,
            timepoint_name="t1",
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
            prepare_if_missing=False,
        )
    )

    assert (
        selection.mode
        == "unavailable"
    )

    assert (
        selection.labelmap_path
        is None
    )

    assert (
        "not prepared yet"
        in selection.status_message
    )



def test_read_only_selection_reports_running_preparation(
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    registration_dir.mkdir(
        parents=True,
    )

    (
        registration_dir
        / "preparation.json"
    ).write_text(
        json.dumps(
            {
                "state": "running",
                "message": "working",
            }
        ),
        encoding="utf-8",
    )

    selection = (
        select_patient_atlas(
            metadata_root=tmp_path,
            patients_root=tmp_path,
            atlas_root=tmp_path,
            patient_id=42,
            timepoint_name="t1",
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
            prepare_if_missing=False,
        )
    )

    assert (
        "being prepared"
        in selection.status_message
    )


def test_read_only_selection_reports_failed_preparation(
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    registration_dir.mkdir(
        parents=True,
    )

    (
        registration_dir
        / "preparation.json"
    ).write_text(
        json.dumps(
            {
                "state": "failed",
                "message": "synthetic failure",
            }
        ),
        encoding="utf-8",
    )

    selection = (
        select_patient_atlas(
            metadata_root=tmp_path,
            patients_root=tmp_path,
            atlas_root=tmp_path,
            patient_id=42,
            timepoint_name="t1",
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
            prepare_if_missing=False,
        )
    )

    assert (
        "synthetic failure"
        in selection.status_message
    )



def test_failed_linear_preview_retries_full_registration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    registration_dir.mkdir(
        parents=True,
    )

    candidate = (
        registration_dir
        / "labels_candidate.nii.gz"
    )

    candidate.write_bytes(
        b"candidate"
    )

    (
        registration_dir
        / "registration.json"
    ).write_text(
        json.dumps(
            {
                "quality": {
                    "status": "fail",
                },
                "config": {
                    "enable_bspline": False,
                },
            }
        ),
        encoding="utf-8",
    )

    calls: list[
        bool
    ] = []

    def fake_prepare(
        **kwargs: object,
    ) -> SimpleNamespace:
        calls.append(
            bool(
                kwargs[
                    "full"
                ]
            )
        )

        return SimpleNamespace(
            candidate_labels_path=(
                candidate
            ),
            quality=(
                SimpleNamespace(
                    status="warn"
                )
            ),
        )

    monkeypatch.setattr(
        anatomy_runtime,
        "_prepare_registration",
        fake_prepare,
    )

    selection = (
        select_patient_atlas(
            metadata_root=tmp_path,
            patients_root=tmp_path,
            atlas_root=tmp_path,
            patient_id=42,
            timepoint_name="t1",
            target_spacing=(
                2.0,
                2.0,
                2.0,
            ),
        )
    )

    assert calls == [
        True,
    ]

    assert (
        selection.mode
        == "automatic-preview"
    )

    assert (
        selection.automatic_qc_status
        == "warn"
    )
