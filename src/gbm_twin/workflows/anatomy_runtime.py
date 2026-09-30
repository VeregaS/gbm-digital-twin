from __future__ import annotations

import json
import shutil
from dataclasses import (
    dataclass,
    replace,
)
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Literal, cast

from gbm_twin.anatomy.bootstrap import (
    bootstrap_harvard_oxford_atlas,
)
from gbm_twin.anatomy.registration import (
    DEFAULT_REGISTRATION_CONFIG,
)
from gbm_twin.workflows.anatomy_registration import (
    prepare_patient_registered_atlas,
)

AtlasSelectionMode = Literal[
    "manual",
    "automatic-preview",
    "unavailable",
]

_REQUIRED_ATLAS_FILES = (
    "manifest.json",
    "template_t1.nii.gz",
    "template_brain_mask.nii.gz",
    "template_labels.nii.gz",
)

_BOOTSTRAP_LOCK = Lock()
_REGISTRATION_LOCK = Lock()

PREVIEW_REGISTRATION_CONFIG = (
    replace(
        DEFAULT_REGISTRATION_CONFIG,
        enable_bspline=False,
    )
)


@dataclass(frozen=True)
class PatientAtlasSelection:
    mode: AtlasSelectionMode
    labelmap_path: Path | None
    automatic_qc_status: str | None
    status_message: str


def _json_mapping(
    path: Path,
) -> dict[str, object]:
    raw: object = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            f"{path.name} must contain a JSON object"
        )

    return cast(
        dict[str, object],
        raw,
    )


def _quality_status(
    registration_path: Path,
) -> str:
    payload = _json_mapping(
        registration_path
    )

    quality = payload.get(
        "quality"
    )

    if not isinstance(
        quality,
        dict,
    ):
        raise ValueError(
            "registration.json is missing quality"
        )

    status = str(
        quality.get(
            "status",
            "",
        )
    ).strip().lower()

    if status not in {
        "pass",
        "warn",
        "fail",
    }:
        raise ValueError(
            "registration.json contains an invalid quality status"
        )

    return status


def ensure_atlas_assets(
    atlas_root: Path,
) -> Path:
    atlas_root = (
        atlas_root.resolve()
    )

    required = tuple(
        atlas_root / filename
        for filename in (
            _REQUIRED_ATLAS_FILES
        )
    )

    if all(
        path.is_file()
        for path in required
    ):
        return atlas_root

    with _BOOTSTRAP_LOCK:
        if all(
            path.is_file()
            for path in required
        ):
            return atlas_root

        atlas_root.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        atlas_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        with TemporaryDirectory(
            prefix="gbm-twin-atlas-bootstrap-",
            dir=str(
                atlas_root.parent
            ),
        ) as temporary_directory:
            temporary_root = Path(
                temporary_directory
            )

            bootstrap_harvard_oxford_atlas(
                temporary_root
            )

            for filename in (
                _REQUIRED_ATLAS_FILES
            ):
                shutil.copy2(
                    temporary_root
                    / filename,
                    atlas_root
                    / filename,
                )

    return atlas_root


def select_patient_atlas(
    *,
    metadata_root: Path,
    patients_root: Path,
    atlas_root: Path,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ],
) -> PatientAtlasSelection:
    normalized_timepoint = (
        timepoint_name
        .strip()
        .lower()
    )

    registration_dir = (
        atlas_root.resolve()
        / "patients"
        / str(
            patient_id
        )
        / normalized_timepoint
    )

    canonical_path = (
        registration_dir
        / "labels.nii.gz"
    )

    candidate_path = (
        registration_dir
        / "labels_candidate.nii.gz"
    )

    registration_path = (
        registration_dir
        / "registration.json"
    )

    review_path = (
        registration_dir
        / "review.json"
    )

    if review_path.is_file():
        try:
            review = _json_mapping(
                review_path
            )

            decision = str(
                review.get(
                    "decision",
                    "",
                )
            ).strip().lower()

        except (
            json.JSONDecodeError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            return PatientAtlasSelection(
                mode="unavailable",
                labelmap_path=None,
                automatic_qc_status=None,
                status_message=(
                    "Atlas review metadata is invalid: "
                    f"{exc}"
                ),
            )

        if decision == "rejected":
            return PatientAtlasSelection(
                mode="unavailable",
                labelmap_path=None,
                automatic_qc_status=None,
                status_message=(
                    "The patient atlas registration was manually rejected."
                ),
            )

        if decision == "accepted":
            if (
                not canonical_path.is_file()
                or not registration_path.is_file()
            ):
                return PatientAtlasSelection(
                    mode="unavailable",
                    labelmap_path=None,
                    automatic_qc_status=None,
                    status_message=(
                        "Accepted atlas review is incomplete."
                    ),
                )

            try:
                quality_status = (
                    _quality_status(
                        registration_path
                    )
                )
            except (
                json.JSONDecodeError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                return PatientAtlasSelection(
                    mode="unavailable",
                    labelmap_path=None,
                    automatic_qc_status=None,
                    status_message=str(
                        exc
                    ),
                )

            return PatientAtlasSelection(
                mode="manual",
                labelmap_path=(
                    canonical_path
                ),
                automatic_qc_status=(
                    quality_status
                ),
                status_message=(
                    "Manually accepted patient-space atlas registration."
                ),
            )

        return PatientAtlasSelection(
            mode="unavailable",
            labelmap_path=None,
            automatic_qc_status=None,
            status_message=(
                "Atlas review has an unsupported decision."
            ),
        )

    with _REGISTRATION_LOCK:
        if (
            candidate_path.is_file()
            and registration_path.is_file()
        ):
            quality_status = (
                _quality_status(
                    registration_path
                )
            )
        else:
            result = (
                prepare_patient_registered_atlas(
                    metadata_root=(
                        metadata_root
                    ),
                    patients_root=(
                        patients_root
                    ),
                    atlas_root=(
                        atlas_root
                    ),
                    patient_id=(
                        patient_id
                    ),
                    timepoint_name=(
                        normalized_timepoint
                    ),
                    target_spacing=(
                        target_spacing
                    ),
                    config=(
                        PREVIEW_REGISTRATION_CONFIG
                    ),
                )
            )

            candidate_path = (
                result
                .candidate_labels_path
            )

            quality_status = (
                result
                .quality
                .status
                .strip()
                .lower()
            )

    if quality_status == "fail":
        return PatientAtlasSelection(
            mode="unavailable",
            labelmap_path=None,
            automatic_qc_status=(
                quality_status
            ),
            status_message=(
                "Automatic atlas registration QC failed. "
                "The candidate is not used."
            ),
        )

    if quality_status not in {
        "pass",
        "warn",
    }:
        return PatientAtlasSelection(
            mode="unavailable",
            labelmap_path=None,
            automatic_qc_status=(
                quality_status
            ),
            status_message=(
                "Automatic atlas registration returned an unsupported QC status."
            ),
        )

    return PatientAtlasSelection(
        mode="automatic-preview",
        labelmap_path=(
            candidate_path
        ),
        automatic_qc_status=(
            quality_status
        ),
        status_message=(
            "Automatic-QC atlas preview. Manual review is still pending."
        ),
    )
