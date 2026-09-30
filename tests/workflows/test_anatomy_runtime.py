import json
from pathlib import Path

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
