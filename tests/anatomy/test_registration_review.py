import json
from pathlib import Path

import pytest

from gbm_twin.anatomy.registration_review import (
    review_registration,
)


def _write_registration(
    directory: Path,
    *,
    status: str,
) -> None:
    payload = {
        "quality": {
            "status": status,
            "brain_dice": 0.82,
            (
                "labeled_inside_"
                "brain_fraction"
            ): 0.87,
        }
    }

    (
        directory
        / "registration.json"
    ).write_text(
        json.dumps(
            payload
        ),
        encoding="utf-8",
    )


def test_accept_registration(
    tmp_path: Path,
) -> None:
    candidate = (
        tmp_path
        / "labels_candidate.nii.gz"
    )

    candidate.write_bytes(
        b"candidate-data"
    )

    _write_registration(
        tmp_path,
        status="warn",
    )

    review = (
        review_registration(
            registration_dir=(
                tmp_path
            ),
            patient_id=108,
            timepoint_name="t1",
            decision="accepted",
            reviewer="researcher",
            notes=(
                "Visual QC accepted."
            ),
        )
    )

    accepted = (
        tmp_path
        / "labels.nii.gz"
    )

    assert accepted.is_file()

    assert (
        accepted.read_bytes()
        == candidate.read_bytes()
    )

    assert (
        review.decision
        == "accepted"
    )

    assert (
        tmp_path
        / "review.json"
    ).is_file()


def test_reject_registration(
    tmp_path: Path,
) -> None:
    (
        tmp_path
        / "labels_candidate.nii.gz"
    ).write_bytes(
        b"candidate-data"
    )

    (
        tmp_path
        / "labels.nii.gz"
    ).write_bytes(
        b"old-accepted-data"
    )

    _write_registration(
        tmp_path,
        status="warn",
    )

    review_registration(
        registration_dir=(
            tmp_path
        ),
        patient_id=108,
        timepoint_name="t1",
        decision="rejected",
        reviewer="researcher",
    )

    assert not (
        tmp_path
        / "labels.nii.gz"
    ).exists()


def test_cannot_accept_failed_qc(
    tmp_path: Path,
) -> None:
    (
        tmp_path
        / "labels_candidate.nii.gz"
    ).write_bytes(
        b"candidate-data"
    )

    _write_registration(
        tmp_path,
        status="fail",
    )

    with pytest.raises(
        ValueError,
        match=(
            "cannot be accepted"
        ),
    ):
        review_registration(
            registration_dir=(
                tmp_path
            ),
            patient_id=108,
            timepoint_name="t1",
            decision="accepted",
            reviewer="researcher",
        )