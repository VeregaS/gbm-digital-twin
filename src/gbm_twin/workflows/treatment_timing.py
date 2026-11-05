from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)
from gbm_twin.models.rt_schedule import (
    reconstruct_weekday_like_schedule,
)
from gbm_twin.workflows.provenance import sha256_file

TREATMENT_TIMING_AUDIT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class TreatmentTimingRecord:
    patient_id: int
    t1_day: float | None

    treatment_reconstructable: bool
    rt_start_day: float | None
    total_dose_gy: float | None
    fractions_number: int | None

    last_fraction_day: float | None
    rt_completed_by_t1: bool | None
    fractions_after_t1: int | None
    days_from_last_fraction_to_t1: float | None


@dataclass(frozen=True)
class TreatmentTimingAuditResult:
    directory: Path
    records: tuple[TreatmentTimingRecord, ...]
    summary: dict[str, int]


def derive_treatment_timing(
    *,
    patient_id: int,
    t1_day: float | None,
    rt_start_day: float | None,
    total_dose_gy: float | None,
    fractions_number: int | None,
) -> TreatmentTimingRecord:
    reconstructable = (
        rt_start_day is not None
        and total_dose_gy is not None
        and total_dose_gy > 0.0
        and fractions_number is not None
        and fractions_number > 0
    )

    if not reconstructable:
        return TreatmentTimingRecord(
            patient_id=patient_id,
            t1_day=t1_day,
            treatment_reconstructable=False,
            rt_start_day=rt_start_day,
            total_dose_gy=total_dose_gy,
            fractions_number=fractions_number,
            last_fraction_day=None,
            rt_completed_by_t1=None,
            fractions_after_t1=None,
            days_from_last_fraction_to_t1=None,
        )

    assert rt_start_day is not None
    assert total_dose_gy is not None
    assert fractions_number is not None

    schedule = reconstruct_weekday_like_schedule(
        start_day=rt_start_day,
        total_dose_gy=total_dose_gy,
        fractions_number=fractions_number,
    )

    last_fraction_day = schedule.fraction_days[-1]

    if t1_day is None:
        return TreatmentTimingRecord(
            patient_id=patient_id,
            t1_day=None,
            treatment_reconstructable=True,
            rt_start_day=rt_start_day,
            total_dose_gy=total_dose_gy,
            fractions_number=fractions_number,
            last_fraction_day=last_fraction_day,
            rt_completed_by_t1=None,
            fractions_after_t1=None,
            days_from_last_fraction_to_t1=None,
        )

    fractions_after_t1 = sum(
        fraction_day > t1_day
        for fraction_day in schedule.fraction_days
    )

    return TreatmentTimingRecord(
        patient_id=patient_id,
        t1_day=t1_day,
        treatment_reconstructable=True,
        rt_start_day=rt_start_day,
        total_dose_gy=total_dose_gy,
        fractions_number=fractions_number,
        last_fraction_day=last_fraction_day,
        rt_completed_by_t1=(
            last_fraction_day <= t1_day
        ),
        fractions_after_t1=fractions_after_t1,
        days_from_last_fraction_to_t1=(
            t1_day - last_fraction_day
        ),
    )


def _resolve_from_repo(
    repo_root: Path,
    path: Path,
) -> Path:
    if path.is_absolute():
        return path

    return repo_root / path


def _record_for_patient(
    *,
    metadata: CFBMetadata,
    treatment_metadata: CFBTreatmentMetadata,
    patient_id: int,
) -> TreatmentTimingRecord:
    patient = metadata.patient(patient_id)

    try:
        t1 = patient.get_timepoint("t1")
    except (KeyError, ValueError):
        t1_day: float | None = None
    else:
        raw_t1_day = t1.days_from_baseline
        t1_day = (
            None
            if raw_t1_day is None
            else float(raw_t1_day)
        )

    treatment = treatment_metadata.treatment(
        patient_id
    )

    if treatment is None:
        return derive_treatment_timing(
            patient_id=patient_id,
            t1_day=t1_day,
            rt_start_day=None,
            total_dose_gy=None,
            fractions_number=None,
        )

    return derive_treatment_timing(
        patient_id=patient_id,
        t1_day=t1_day,
        rt_start_day=(
            treatment.radiotherapy_start_day
        ),
        total_dose_gy=treatment.dose_gy,
        fractions_number=(
            treatment.fractions_number
        ),
    )


def _summary(
    records: tuple[TreatmentTimingRecord, ...],
) -> dict[str, int]:
    reconstructable = [
        record
        for record in records
        if record.treatment_reconstructable
    ]

    completed = [
        record
        for record in reconstructable
        if record.rt_completed_by_t1 is True
    ]

    future_fractions = [
        record
        for record in reconstructable
        if (
            record.fractions_after_t1 is not None
            and record.fractions_after_t1 > 0
        )
    ]

    return {
        "patient_count": len(records),
        "treatment_reconstructable_count": len(
            reconstructable
        ),
        "rt_completed_by_t1_count": len(
            completed
        ),
        "patients_with_future_rt_fractions_count": len(
            future_fractions
        ),
    }


def _write_csv(
    path: Path,
    records: tuple[TreatmentTimingRecord, ...],
) -> None:
    fieldnames = [
        "patient_id",
        "t1_day",
        "treatment_reconstructable",
        "rt_start_day",
        "total_dose_gy",
        "fractions_number",
        "last_fraction_day",
        "rt_completed_by_t1",
        "fractions_after_t1",
        "days_from_last_fraction_to_t1",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )

        writer.writeheader()

        for record in records:
            writer.writerow(
                asdict(record)
            )


def build_treatment_timing_audit(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    output_dir: Path,
) -> TreatmentTimingAuditResult:
    root = repo_root.resolve()
    experiment_path = _resolve_from_repo(
        root,
        experiment_config_path,
    ).resolve()

    experiment = load_cohort_experiment_config(
        experiment_path
    )

    metadata_root = _resolve_from_repo(
        root,
        experiment.metadata_root,
    )

    metadata = CFBMetadata(
        metadata_root
    )
    treatment_metadata = CFBTreatmentMetadata(
        metadata_root
    )

    records = tuple(
        _record_for_patient(
            metadata=metadata,
            treatment_metadata=treatment_metadata,
            patient_id=patient_id,
        )
        for patient_id in experiment.patient_ids
    )

    summary = _summary(records)

    destination = _resolve_from_repo(
        root,
        output_dir,
    ).resolve()

    if destination.exists():
        raise FileExistsError(
            "Treatment timing audit destination "
            f"already exists: {destination}"
        )

    destination.mkdir(
        parents=True,
        exist_ok=False,
    )

    payload = {
        "schema_version": (
            TREATMENT_TIMING_AUDIT_SCHEMA_VERSION
        ),
        "kind": "pre_t2_treatment_timing_audit",
        "uses_t2_observation": False,
        "experiment_config_file": (
            experiment_path.name
        ),
        "experiment_config_sha256": (
            sha256_file(experiment_path)
        ),
        "summary": summary,
        "patients": [
            asdict(record)
            for record in records
        ],
    }

    json_path = (
        destination
        / "treatment_timing_audit.json"
    )

    json_path.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    (
        destination
        / "treatment_timing_audit.sha256"
    ).write_text(
        sha256_file(json_path)
        + "  treatment_timing_audit.json\n",
        encoding="ascii",
    )

    _write_csv(
        destination
        / "treatment_timing_audit.csv",
        records,
    )

    return TreatmentTimingAuditResult(
        directory=destination,
        records=records,
        summary=summary,
    )
