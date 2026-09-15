from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import (
    asdict,
    dataclass,
)
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path
from typing import Literal

ReviewDecision = Literal[
    "accepted",
    "rejected",
]


@dataclass(frozen=True)
class RegistrationReview:
    patient_id: int

    timepoint_name: str

    decision: ReviewDecision

    reviewer: str

    notes: str | None

    reviewed_at_utc: str

    automatic_qc_status: str

    candidate_sha256: str

    registration_sha256: str


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def _read_registration(
    path: Path,
) -> dict[str, object]:
    if not path.is_file():
        raise FileNotFoundError(
            "Registration provenance "
            f"not found: {path}"
        )

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            "registration.json "
            "must contain an object"
        )

    return raw


def _automatic_status(
    payload: dict[str, object],
) -> str:
    quality = payload.get(
        "quality"
    )

    if not isinstance(
        quality,
        dict,
    ):
        raise ValueError(
            "registration.json "
            "contains no quality object"
        )

    status = quality.get(
        "status"
    )

    if not isinstance(
        status,
        str,
    ):
        raise ValueError(
            "registration.json "
            "contains no quality status"
        )

    return status


def _atomic_copy(
    source: Path,
    destination: Path,
) -> None:
    temporary = destination.with_name(
        destination.name
        + ".tmp"
    )

    shutil.copy2(
        source,
        temporary,
    )

    os.replace(
        temporary,
        destination,
    )


def review_registration(
    *,
    registration_dir: Path,
    patient_id: int,
    timepoint_name: str,
    decision: ReviewDecision,
    reviewer: str,
    notes: str | None = None,
) -> RegistrationReview:
    registration_dir = (
        registration_dir.resolve()
    )

    normalized_timepoint = (
        timepoint_name
        .strip()
        .lower()
    )

    normalized_reviewer = (
        reviewer.strip()
    )

    if patient_id <= 0:
        raise ValueError(
            "patient_id must be positive"
        )

    if normalized_timepoint not in {
        "t0",
        "t1",
        "t2",
    }:
        raise ValueError(
            "timepoint_name must "
            "be t0, t1 or t2"
        )

    if decision not in {
        "accepted",
        "rejected",
    }:
        raise ValueError(
            "decision must be "
            "accepted or rejected"
        )

    if not normalized_reviewer:
        raise ValueError(
            "reviewer must not be empty"
        )

    candidate_path = (
        registration_dir
        / "labels_candidate.nii.gz"
    )

    registration_path = (
        registration_dir
        / "registration.json"
    )

    accepted_path = (
        registration_dir
        / "labels.nii.gz"
    )

    review_path = (
        registration_dir
        / "review.json"
    )

    if not candidate_path.is_file():
        raise FileNotFoundError(
            "Registration candidate "
            f"not found: {candidate_path}"
        )

    registration = (
        _read_registration(
            registration_path
        )
    )

    automatic_status = (
        _automatic_status(
            registration
        )
    )

    if (
        decision == "accepted"
        and automatic_status == "fail"
    ):
        raise ValueError(
            "A registration with "
            "automatic QC status 'fail' "
            "cannot be accepted"
        )

    candidate_hash = (
        _sha256(
            candidate_path
        )
    )

    registration_hash = (
        _sha256(
            registration_path
        )
    )

    normalized_notes = (
        notes.strip()
        if (
            notes is not None
            and notes.strip()
        )
        else None
    )

    review = RegistrationReview(
        patient_id=patient_id,
        timepoint_name=(
            normalized_timepoint
        ),
        decision=decision,
        reviewer=(
            normalized_reviewer
        ),
        notes=(
            normalized_notes
        ),
        reviewed_at_utc=(
            datetime.now(
                UTC
            ).isoformat()
        ),
        automatic_qc_status=(
            automatic_status
        ),
        candidate_sha256=(
            candidate_hash
        ),
        registration_sha256=(
            registration_hash
        ),
    )

    if decision == "accepted":
        _atomic_copy(
            candidate_path,
            accepted_path,
        )

    else:
        accepted_path.unlink(
            missing_ok=True
        )

    review_path.write_text(
        json.dumps(
            asdict(
                review
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return review