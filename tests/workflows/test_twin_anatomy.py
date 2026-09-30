from __future__ import annotations

import hashlib
import json
from pathlib import Path

from gbm_twin.workflows.twin_anatomy import (
    TwinAnatomicalRegionImpact,
    build_anatomical_changes,
    verify_t1_atlas_review,
)


def _sha256(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def test_verified_review_requires_accepted_canonical_labelmap(
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    registration_dir.mkdir(
        parents=True
    )

    labelmap = (
        registration_dir
        / "labels.nii.gz"
    )

    registration = (
        registration_dir
        / "registration.json"
    )

    labelmap.write_bytes(
        b"accepted-labelmap"
    )

    registration.write_text(
        '{"quality":{"status":"pass"}}',
        encoding="utf-8",
    )

    (
        registration_dir
        / "review.json"
    ).write_text(
        json.dumps(
            {
                "patient_id": 42,
                "timepoint_name": "t1",
                "decision": "accepted",
                "reviewer": "researcher",
                "notes": None,
                "reviewed_at_utc": (
                    "2026-09-30T00:00:00+00:00"
                ),
                "automatic_qc_status": "pass",
                "candidate_sha256": (
                    _sha256(
                        labelmap
                    )
                ),
                "registration_sha256": (
                    _sha256(
                        registration
                    )
                ),
            }
        ),
        encoding="utf-8",
    )

    evidence = (
        verify_t1_atlas_review(
            atlas_root=tmp_path,
            patient_id=42,
        )
    )

    assert evidence.verified
    assert (
        evidence.decision
        == "accepted"
    )
    assert (
        evidence.automatic_qc_status
        == "pass"
    )


def test_review_is_invalidated_when_labelmap_changes(
    tmp_path: Path,
) -> None:
    registration_dir = (
        tmp_path
        / "patients"
        / "42"
        / "t1"
    )

    registration_dir.mkdir(
        parents=True
    )

    labelmap = (
        registration_dir
        / "labels.nii.gz"
    )

    registration = (
        registration_dir
        / "registration.json"
    )

    labelmap.write_bytes(
        b"accepted-labelmap"
    )

    registration.write_text(
        '{"quality":{"status":"pass"}}',
        encoding="utf-8",
    )

    original_hash = _sha256(
        labelmap
    )

    (
        registration_dir
        / "review.json"
    ).write_text(
        json.dumps(
            {
                "patient_id": 42,
                "timepoint_name": "t1",
                "decision": "accepted",
                "reviewed_at_utc": (
                    "2026-09-30T00:00:00+00:00"
                ),
                "automatic_qc_status": "pass",
                "candidate_sha256": (
                    original_hash
                ),
                "registration_sha256": (
                    _sha256(
                        registration
                    )
                ),
            }
        ),
        encoding="utf-8",
    )

    labelmap.write_bytes(
        b"modified-after-review"
    )

    evidence = (
        verify_t1_atlas_review(
            atlas_root=tmp_path,
            patient_id=42,
        )
    )

    assert not evidence.verified
    assert (
        "does not match reviewed candidate"
        in evidence.status_message
    )


def _impact(
    label: int,
    name: str,
) -> TwinAnatomicalRegionImpact:
    return TwinAnatomicalRegionImpact(
        severity="moderate",
        region_label=label,
        region_name=name,
        category="language",
        laterality="left",
        functional_note=None,
        mask_overlap_cm3=0.0,
        density_overlap_cm3=0.1,
        min_distance_mm=2.0,
    )


def test_anatomical_changes_classify_new_persistent_and_resolved(
) -> None:
    changes = build_anatomical_changes(
        (
            _impact(
                1,
                "Current only",
            ),
            _impact(
                2,
                "Persistent",
            ),
        ),
        (
            _impact(
                2,
                "Persistent",
            ),
            _impact(
                3,
                "Forecast only",
            ),
        ),
    )

    assert [
        (
            item.region_label,
            item.status,
        )
        for item in changes
    ] == [
        (3, "new"),
        (2, "persistent"),
        (1, "resolved"),
    ]
