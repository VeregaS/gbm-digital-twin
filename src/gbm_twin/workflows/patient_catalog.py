from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)

_TIMEPOINT_NAMES = (
    "t0",
    "t1",
    "t2",
)

_PATIENT_ID_PATTERN = re.compile(
    r"(\d+)$"
)


@dataclass(frozen=True)
class PatientCatalogTimepoint:
    name: str
    days_from_baseline: float | None

    gtv_available: bool | None
    gtv_type: str | None

    rtdose_available: bool | None


@dataclass(frozen=True)
class PatientTreatmentSummary:
    has_record: bool

    rt_start_day: float | None
    rt_start_phase: str

    rt_started_by_t1: bool | None
    rt_started_by_t2: bool | None

    dose_gy: float | None
    fractions: int | None

    reconstructable: bool


@dataclass(frozen=True)
class PatientCatalogSummary:
    patient_id: int

    timepoints: tuple[
        PatientCatalogTimepoint,
        ...,
    ]

    dt01_days: float | None
    dt12_days: float | None

    treatment: PatientTreatmentSummary

    @property
    def timepoint_count(self) -> int:
        return len(self.timepoints)


def discover_patient_ids(
    patients_root: Path,
) -> tuple[int, ...]:
    if not patients_root.exists():
        raise FileNotFoundError(
            f"Patients root does not exist: "
            f"{patients_root}"
        )

    if not patients_root.is_dir():
        raise NotADirectoryError(
            f"Patients root is not a directory: "
            f"{patients_root}"
        )

    patient_ids: set[int] = set()

    for path in patients_root.iterdir():
        if not path.is_dir():
            continue

        match = _PATIENT_ID_PATTERN.search(
            path.name
        )

        if match is None:
            continue

        patient_ids.add(
            int(match.group(1))
        )

    return tuple(
        sorted(patient_ids)
    )


def _interval_days(
    start_day: float | None,
    end_day: float | None,
) -> float | None:
    if (
        start_day is None
        or end_day is None
    ):
        return None

    duration = end_day - start_day

    if duration <= 0:
        return None

    return float(duration)


def _build_treatment_summary(
    *,
    treatment_metadata: CFBTreatmentMetadata,
    patient_id: int,
    dt01_days: float | None,
    dt12_days: float | None,
) -> PatientTreatmentSummary:
    treatment = (
        treatment_metadata.treatment(
            patient_id
        )
    )

    if treatment is None:
        return PatientTreatmentSummary(
            has_record=False,
            rt_start_day=None,
            rt_start_phase="unknown",
            rt_started_by_t1=None,
            rt_started_by_t2=None,
            dose_gy=None,
            fractions=None,
            reconstructable=False,
        )

    reconstructable = (
        treatment.radiotherapy_start_day
        is not None
        and treatment.dose_gy is not None
        and treatment.dose_gy > 0
        and treatment.fractions_number
        is not None
        and treatment.fractions_number > 0
    )

    if (
        dt01_days is not None
        and dt12_days is not None
    ):
        context = (
            treatment_metadata.patient_context(
                patient_id,
                dt01_days=dt01_days,
                dt12_days=dt12_days,
            )
        )

        return PatientTreatmentSummary(
            has_record=(
                context.has_treatment_record
            ),
            rt_start_day=(
                context.rt_start_day
            ),
            rt_start_phase=(
                context.rt_start_phase
            ),
            rt_started_by_t1=(
                context.rt_started_by_t1
            ),
            rt_started_by_t2=(
                context.rt_started_by_t2
            ),
            dose_gy=context.rt_dose_gy,
            fractions=context.rt_fractions,
            reconstructable=reconstructable,
        )

    return PatientTreatmentSummary(
        has_record=True,
        rt_start_day=(
            treatment.radiotherapy_start_day
        ),
        rt_start_phase="unknown",
        rt_started_by_t1=None,
        rt_started_by_t2=None,
        dose_gy=treatment.dose_gy,
        fractions=(
            treatment.fractions_number
        ),
        reconstructable=reconstructable,
    )


def get_patient_catalog_summary(
    *,
    metadata_root: Path,
    patient_id: int,
) -> PatientCatalogSummary:
    metadata = CFBMetadata(
        metadata_root
    )

    treatment_metadata = (
        CFBTreatmentMetadata(
            metadata_root
        )
    )

    patient = metadata.patient(
        patient_id
    )

    imaging_records = (
        treatment_metadata.imaging_records(
            patient_id
        )
    )

    imaging_by_timepoint = {
        record.temporality.strip().lower(): (
            record
        )
        for record in imaging_records
    }

    timepoints: list[
        PatientCatalogTimepoint
    ] = []

    days_by_name: dict[
        str,
        float | None,
    ] = {}

    for name in _TIMEPOINT_NAMES:
        try:
            timepoint = patient.get_timepoint(
                name
            )
        except (KeyError, ValueError):
            continue

        raw_day = (
            timepoint.days_from_baseline
        )

        day = (
            None
            if raw_day is None
            else float(raw_day)
        )

        days_by_name[name] = day

        imaging = (
            imaging_by_timepoint.get(name)
        )

        timepoints.append(
            PatientCatalogTimepoint(
                name=name,
                days_from_baseline=day,
                gtv_available=(
                    None
                    if imaging is None
                    else imaging.gtv_available
                ),
                gtv_type=(
                    None
                    if imaging is None
                    else imaging.gtv_type
                ),
                rtdose_available=(
                    None
                    if imaging is None
                    else imaging.rtdose_available
                ),
            )
        )

    dt01_days = _interval_days(
        days_by_name.get("t0"),
        days_by_name.get("t1"),
    )

    dt12_days = _interval_days(
        days_by_name.get("t1"),
        days_by_name.get("t2"),
    )

    treatment = _build_treatment_summary(
        treatment_metadata=(
            treatment_metadata
        ),
        patient_id=patient_id,
        dt01_days=dt01_days,
        dt12_days=dt12_days,
    )

    return PatientCatalogSummary(
        patient_id=patient_id,
        timepoints=tuple(timepoints),
        dt01_days=dt01_days,
        dt12_days=dt12_days,
        treatment=treatment,
    )