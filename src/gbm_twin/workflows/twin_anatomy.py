from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np

from gbm_twin.anatomy.atlas import (
    load_registered_atlas,
    registered_labelmap_path,
)
from gbm_twin.anatomy.models import AnatomicalWarning
from gbm_twin.anatomy.risk import (
    DEFAULT_LATENT_RISK_LEVEL,
    DEFAULT_PROXIMITY_THRESHOLD_MM,
    compute_anatomical_risk,
)
from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.workflows.anatomy_runtime import (
    select_patient_atlas,
)
from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.patients import prepare_patient_timepoint
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.twin_artifacts import (
    find_evaluated_patient,
    load_frozen_patient_artifact,
    target_spacing,
)

TWIN_ANATOMICAL_LATENT_WIDTH_MM = 4.0

AnatomicalChangeStatus = Literal[
    "new",
    "persistent",
    "resolved",
]


@dataclass(frozen=True)
class TwinAtlasReviewEvidence:
    timepoint_name: str
    verified: bool
    decision: str | None
    automatic_qc_status: str | None
    reviewed_at_utc: str | None
    status_message: str


@dataclass(frozen=True)
class TwinAnatomicalRegionImpact:
    severity: str
    region_label: int
    region_name: str
    category: str
    laterality: str | None
    functional_note: str | None
    mask_overlap_cm3: float
    density_overlap_cm3: float
    min_distance_mm: float | None


@dataclass(frozen=True)
class TwinAnatomicalChange:
    status: AnatomicalChangeStatus
    region_label: int
    region_name: str
    category: str
    laterality: str | None
    functional_note: str | None
    current_severity: str | None
    forecast_severity: str | None


@dataclass(frozen=True)
class TwinAnatomicalImpactReport:
    patient_id: int
    current_timepoint: str
    forecast_timepoint: str
    configured: bool
    atlas_name: str | None
    status_message: str
    registration: TwinAtlasReviewEvidence
    current: tuple[TwinAnatomicalRegionImpact, ...]
    forecast: tuple[TwinAnatomicalRegionImpact, ...]
    changes: tuple[TwinAnatomicalChange, ...]
    latent_level: float = DEFAULT_LATENT_RISK_LEVEL
    proximity_threshold_mm: float = DEFAULT_PROXIMITY_THRESHOLD_MM
    disclaimer: str = (
        "Research-only population-atlas estimate. Atlas-defined functional "
        "associations are not a patient-specific functional map and do not "
        "predict a neurological deficit. The forecast section uses only the "
        "frozen model prediction and does not use observed t2 anatomy."
    )


def _unavailable_review(
    *,
    status_message: str,
) -> TwinAtlasReviewEvidence:
    return TwinAtlasReviewEvidence(
        timepoint_name="t1",
        verified=False,
        decision=None,
        automatic_qc_status=None,
        reviewed_at_utc=None,
        status_message=status_message,
    )


def _unavailable_report(
    *,
    patient_id: int,
    forecast_timepoint: str,
    status_message: str,
    registration: TwinAtlasReviewEvidence | None = None,
) -> TwinAnatomicalImpactReport:
    return TwinAnatomicalImpactReport(
        patient_id=patient_id,
        current_timepoint="t1",
        forecast_timepoint=forecast_timepoint,
        configured=False,
        atlas_name=None,
        status_message=status_message,
        registration=(
            registration
            if registration is not None
            else _unavailable_review(
                status_message=status_message,
            )
        ),
        current=(),
        forecast=(),
        changes=(),
    )


def _review_mapping(
    path: Path,
) -> dict[str, object]:
    raw: object = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(raw, dict):
        raise ValueError(
            f"{path.name} must contain a JSON object"
        )

    return cast(
        dict[str, object],
        raw,
    )


def verify_t1_atlas_review(
    *,
    atlas_root: Path,
    patient_id: int,
) -> TwinAtlasReviewEvidence:
    registration_dir = (
        atlas_root.resolve()
        / "patients"
        / str(patient_id)
        / "t1"
    )

    review_path = (
        registration_dir
        / "review.json"
    )

    registration_path = (
        registration_dir
        / "registration.json"
    )

    labelmap_path = registered_labelmap_path(
        atlas_root,
        patient_id=patient_id,
        timepoint_name="t1",
    )

    required = (
        review_path,
        registration_path,
        labelmap_path,
    )

    missing = [
        path.name
        for path in required
        if not path.is_file()
    ]

    if missing:
        return _unavailable_review(
            status_message=(
                "Anatomical forecast requires an accepted t1 atlas "
                "registration. Missing: "
                + ", ".join(missing)
            )
        )

    try:
        review = _review_mapping(
            review_path
        )

        review_patient_id = review.get(
            "patient_id"
        )

        timepoint_name = str(
            review.get(
                "timepoint_name",
                "",
            )
        ).strip().lower()

        decision = str(
            review.get(
                "decision",
                "",
            )
        ).strip().lower()

        automatic_qc_status = str(
            review.get(
                "automatic_qc_status",
                "",
            )
        ).strip().lower()

        reviewed_at = review.get(
            "reviewed_at_utc"
        )

        candidate_sha256 = str(
            review.get(
                "candidate_sha256",
                "",
            )
        ).strip().lower()

        registration_sha256 = str(
            review.get(
                "registration_sha256",
                "",
            )
        ).strip().lower()

        if review_patient_id != patient_id:
            raise ValueError(
                "review patient_id does not match requested patient"
            )

        if timepoint_name != "t1":
            raise ValueError(
                "review timepoint is not t1"
            )

        if decision != "accepted":
            return TwinAtlasReviewEvidence(
                timepoint_name="t1",
                verified=False,
                decision=decision or None,
                automatic_qc_status=(
                    automatic_qc_status
                    or None
                ),
                reviewed_at_utc=(
                    str(reviewed_at)
                    if reviewed_at is not None
                    else None
                ),
                status_message=(
                    "The t1 atlas registration has not been accepted."
                ),
            )

        if automatic_qc_status == "fail":
            raise ValueError(
                "accepted review cannot reference failed automatic QC"
            )

        if sha256_file(
            labelmap_path
        ) != candidate_sha256:
            raise ValueError(
                "accepted atlas labelmap does not match reviewed candidate"
            )

        if sha256_file(
            registration_path
        ) != registration_sha256:
            raise ValueError(
                "registration provenance changed after manual review"
            )

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        return _unavailable_review(
            status_message=(
                "t1 atlas review could not be verified: "
                f"{exc}"
            )
        )

    return TwinAtlasReviewEvidence(
        timepoint_name="t1",
        verified=True,
        decision="accepted",
        automatic_qc_status=(
            automatic_qc_status
            or None
        ),
        reviewed_at_utc=(
            str(reviewed_at)
            if reviewed_at is not None
            else None
        ),
        status_message=(
            "Accepted t1 atlas registration verified against its "
            "reviewed candidate and registration provenance."
        ),
    )


def _impact_from_warning(
    warning: AnatomicalWarning,
) -> TwinAnatomicalRegionImpact:
    return TwinAnatomicalRegionImpact(
        severity=warning.severity,
        region_label=warning.region_label,
        region_name=warning.region_name,
        category=warning.category,
        laterality=warning.laterality,
        functional_note=warning.functional_note,
        mask_overlap_cm3=(
            warning.observed_overlap_cm3
        ),
        density_overlap_cm3=(
            warning.latent_overlap_cm3
        ),
        min_distance_mm=(
            warning.min_observed_distance_mm
        ),
    )


def build_anatomical_changes(
    current: tuple[TwinAnatomicalRegionImpact, ...],
    forecast: tuple[TwinAnatomicalRegionImpact, ...],
) -> tuple[TwinAnatomicalChange, ...]:
    current_by_label = {
        item.region_label: item
        for item in current
    }

    forecast_by_label = {
        item.region_label: item
        for item in forecast
    }

    changes: list[
        TwinAnatomicalChange
    ] = []

    for label in sorted(
        set(current_by_label)
        | set(forecast_by_label)
    ):
        current_item = (
            current_by_label.get(
                label
            )
        )

        forecast_item = (
            forecast_by_label.get(
                label
            )
        )

        if current_item is None:
            status: AnatomicalChangeStatus = "new"
            reference = forecast_item

        elif forecast_item is None:
            status = "resolved"
            reference = current_item

        else:
            status = "persistent"
            reference = forecast_item

        if reference is None:
            raise RuntimeError(
                "Anatomical change has no reference region"
            )

        changes.append(
            TwinAnatomicalChange(
                status=status,
                region_label=label,
                region_name=(
                    reference.region_name
                ),
                category=(
                    reference.category
                ),
                laterality=(
                    reference.laterality
                ),
                functional_note=(
                    reference.functional_note
                ),
                current_severity=(
                    None
                    if current_item is None
                    else current_item.severity
                ),
                forecast_severity=(
                    None
                    if forecast_item is None
                    else forecast_item.severity
                ),
            )
        )

    status_rank = {
        "new": 0,
        "persistent": 1,
        "resolved": 2,
    }

    return tuple(
        sorted(
            changes,
            key=lambda item: (
                status_rank[
                    item.status
                ],
                item.region_name,
            ),
        )
    )


def analyze_twin_anatomical_impact(
    *,
    metadata_root: Path,
    patients_root: Path,
    atlas_root: Path | None,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    patient_id: int,
) -> TwinAnatomicalImpactReport:
    evaluation = (
        load_sealed_cohort_evaluation(
            cohort_evaluation_root
        )
    )

    payload = evaluation.manifest

    patient = find_evaluated_patient(
        payload,
        patient_id,
    )

    forecast_timepoint = str(
        patient[
            "target_timepoint"
        ]
    ).strip().lower()

    if atlas_root is None:
        return _unavailable_report(
            patient_id=patient_id,
            forecast_timepoint=(
                forecast_timepoint
            ),
            status_message=(
                "Atlas analysis is disabled."
            ),
        )

    spacing = target_spacing(
        payload
    )

    try:
        selection = (
            select_patient_atlas(
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
                timepoint_name="t1",
                target_spacing=(
                    spacing
                ),
                prepare_if_missing=False,
            )
        )
    except (
        FileNotFoundError,
        RuntimeError,
        ValueError,
    ) as exc:
        return _unavailable_report(
            patient_id=patient_id,
            forecast_timepoint=(
                forecast_timepoint
            ),
            status_message=str(
                exc
            ),
        )

    if (
        selection.labelmap_path
        is None
    ):
        registration = (
            _unavailable_review(
                status_message=(
                    selection
                    .status_message
                )
            )
        )

        return _unavailable_report(
            patient_id=patient_id,
            forecast_timepoint=(
                forecast_timepoint
            ),
            status_message=(
                selection
                .status_message
            ),
            registration=registration,
        )

    if (
        selection.mode
        == "manual"
    ):
        registration = (
            verify_t1_atlas_review(
                atlas_root=atlas_root,
                patient_id=patient_id,
            )
        )

        if not registration.verified:
            return _unavailable_report(
                patient_id=patient_id,
                forecast_timepoint=(
                    forecast_timepoint
                ),
                status_message=(
                    registration
                    .status_message
                ),
                registration=registration,
            )
    else:
        registration = (
            TwinAtlasReviewEvidence(
                timepoint_name="t1",
                verified=False,
                decision=(
                    "automatic-preview"
                ),
                automatic_qc_status=(
                    selection
                    .automatic_qc_status
                ),
                reviewed_at_utc=None,
                status_message=(
                    selection
                    .status_message
                ),
            )
        )

    current = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t1",
        target_spacing=spacing,
    )

    atlas = load_registered_atlas(
        atlas_root,
        patient_id=patient_id,
        timepoint_name="t1",
        expected_shape=(
            current.gtv.data.shape
        ),
        expected_affine=(
            current.gtv.affine
        ),
        labelmap_path=(
            selection
            .labelmap_path
        ),
    )

    artifact = (
        load_frozen_patient_artifact(
            cohort_freeze_root=(
                cohort_freeze_root
            ),
            payload=payload,
            patient_id=patient_id,
        )
    )

    current_mask = np.asarray(
        current.gtv.data > 0.5,
        dtype=bool,
    )

    current_density = (
        latent_state_from_gtv(
            current.gtv.data,
            current.brain_mask.data,
            spacing=current.spacing,
            parameters=(
                LatentStateParameters(
                    transition_width_mm=(
                        TWIN_ANATOMICAL_LATENT_WIDTH_MM
                    ),
                )
            ),
        )
    )

    forecast_mask = np.asarray(
        artifact.prediction_mask,
        dtype=bool,
    )

    forecast_density = np.asarray(
        artifact.prediction_field,
        dtype=np.float32,
    )

    expected_shape = (
        current_mask.shape
    )

    if (
        forecast_mask.shape
        != expected_shape
        or forecast_density.shape
        != expected_shape
    ):
        raise ValueError(
            "Frozen prediction and accepted t1 atlas do not share "
            "the same prepared grid"
        )

    current_report = (
        compute_anatomical_risk(
            patient_id=patient_id,
            timepoint_name="t1",
            labelmap=atlas.labelmap,
            regions=atlas.regions,
            gtv_mask=current_mask,
            latent_state=(
                current_density
            ),
            spacing=current.spacing,
            atlas_name=atlas.name,
        )
    )

    forecast_report = (
        compute_anatomical_risk(
            patient_id=patient_id,
            timepoint_name=(
                forecast_timepoint
            ),
            labelmap=atlas.labelmap,
            regions=atlas.regions,
            gtv_mask=forecast_mask,
            latent_state=(
                forecast_density
            ),
            spacing=current.spacing,
            atlas_name=atlas.name,
        )
    )

    current_impacts = tuple(
        _impact_from_warning(
            warning
        )
        for warning in (
            current_report.warnings
        )
    )

    forecast_impacts = tuple(
        _impact_from_warning(
            warning
        )
        for warning in (
            forecast_report.warnings
        )
    )

    return TwinAnatomicalImpactReport(
        patient_id=patient_id,
        current_timepoint="t1",
        forecast_timepoint=(
            forecast_timepoint
        ),
        configured=True,
        atlas_name=atlas.name,
        status_message=(
            "Current t1 and frozen forecast were analyzed on the same "
            + (
                "manually accepted patient-space t1 atlas."
                if registration.verified
                else (
                    "automatic-QC patient-space t1 atlas preview. "
                    "Manual review is still pending."
                )
            )
        ),
        registration=registration,
        current=current_impacts,
        forecast=forecast_impacts,
        changes=(
            build_anatomical_changes(
                current_impacts,
                forecast_impacts,
            )
        ),
    )
