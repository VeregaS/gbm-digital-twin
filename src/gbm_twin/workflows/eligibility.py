from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.dataset_manifest import CFBDatasetManifest


class EligibilityReason(StrEnum):
    UNKNOWN_PATIENT = "unknown_patient"
    MISSING_REQUIRED_TIMEPOINT = "missing_required_timepoint"
    MISSING_REQUIRED_MODALITY = "missing_required_modality"
    MISSING_PREPARED_FILE = "missing_prepared_file"
    INVALID_TIME_INTERVAL = "invalid_time_interval"
    INVALID_GEOMETRY = "invalid_geometry"
    TREATMENT_SCHEDULE_UNAVAILABLE = "treatment_schedule_unavailable"


@dataclass(frozen=True)
class EligibilityIssue:
    reason: EligibilityReason
    detail: str


@dataclass(frozen=True)
class PatientEligibility:
    patient_id: int
    issues: tuple[EligibilityIssue, ...]

    @property
    def eligible(self) -> bool:
        return not self.issues

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(
            issue.reason.value
            for issue in self.issues
        )


def _prepared_file_path(
    *,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    template: str,
) -> Path:
    filename = template.format(
        patient_id=patient_id,
        timepoint=timepoint_name,
    )

    return (
        patients_root
        / str(patient_id)
        / timepoint_name
        / filename
    )


def _validate_time_intervals(
    *,
    metadata: CFBMetadata,
    patient_id: int,
    required_timepoints: tuple[str, ...],
) -> EligibilityIssue | None:
    if len(required_timepoints) < 2:
        return None

    try:
        patient = metadata.patient(
            patient_id
        )

        for index in range(
            len(required_timepoints) - 1
        ):
            start_name = (
                required_timepoints[
                    index
                ]
            )

            end_name = (
                required_timepoints[
                    index + 1
                ]
            )

            patient.interval_days(
                start_name,
                end_name,
            )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return EligibilityIssue(
            reason=(
                EligibilityReason
                .INVALID_TIME_INTERVAL
            ),
            detail=str(exc),
        )

    return None


def assess_patient_eligibility(
    *,
    metadata: CFBMetadata,
    manifest: CFBDatasetManifest,
    patients_root: Path,
    patient_id: int,
) -> PatientEligibility:
    issues: list[
        EligibilityIssue
    ] = []

    known_patient_ids = set(
        metadata.patient_ids()
    )

    if (
        patient_id
        not in known_patient_ids
    ):
        return PatientEligibility(
            patient_id=patient_id,
            issues=(
                EligibilityIssue(
                    reason=(
                        EligibilityReason
                        .UNKNOWN_PATIENT
                    ),
                    detail=(
                        f"Patient {patient_id} "
                        "is not present in "
                        "CFB metadata"
                    ),
                ),
            ),
        )

    available_timepoints = (
        metadata.timepoints(
            patient_id
        )
    )

    missing_timepoints = tuple(
        timepoint_name
        for timepoint_name
        in manifest.required_timepoints
        if timepoint_name
        not in available_timepoints
    )

    for timepoint_name in (
        missing_timepoints
    ):
        issues.append(
            EligibilityIssue(
                reason=(
                    EligibilityReason
                    .MISSING_REQUIRED_TIMEPOINT
                ),
                detail=(
                    f"Patient {patient_id} "
                    "is missing required "
                    f"timepoint "
                    f"{timepoint_name!r}"
                ),
            )
        )

    for timepoint_name in (
        manifest.required_timepoints
    ):
        if (
            timepoint_name
            not in available_timepoints
        ):
            continue

        for modality in (
            manifest.required_modalities
        ):
            if not metadata.has_modality(
                patient_id,
                timepoint_name,
                modality,
            ):
                issues.append(
                    EligibilityIssue(
                        reason=(
                            EligibilityReason
                            .MISSING_REQUIRED_MODALITY
                        ),
                        detail=(
                            f"Patient "
                            f"{patient_id} "
                            f"{timepoint_name}: "
                            "missing required "
                            f"modality "
                            f"{modality!r}"
                        ),
                    )
                )

        for template in (
            manifest
            .required_patient_files
        ):
            path = (
                _prepared_file_path(
                    patients_root=(
                        patients_root
                    ),
                    patient_id=(
                        patient_id
                    ),
                    timepoint_name=(
                        timepoint_name
                    ),
                    template=template,
                )
            )

            if not path.is_file():
                issues.append(
                    EligibilityIssue(
                        reason=(
                            EligibilityReason
                            .MISSING_PREPARED_FILE
                        ),
                        detail=(
                            f"Missing prepared "
                            f"patient file: "
                            f"{path}"
                        ),
                    )
                )

    if not missing_timepoints:
        interval_issue = (
            _validate_time_intervals(
                metadata=metadata,
                patient_id=patient_id,
                required_timepoints=(
                    manifest
                    .required_timepoints
                ),
            )
        )

        if interval_issue is not None:
            issues.append(
                interval_issue
            )

    return PatientEligibility(
        patient_id=patient_id,
        issues=tuple(
            issues
        ),
    )