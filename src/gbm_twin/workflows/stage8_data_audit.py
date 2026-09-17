from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import pandas as pd

from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_protocol import (
    Stage8ProtocolConfig,
    load_stage8_protocol_config,
)

STAGE8_DATA_AUDIT_SCHEMA_VERSION = 1

_MODALITY_ALIASES: dict[str, tuple[str, ...]] = {
    "t1gd": ("t1gd", "t1ce", "t1c", "t1post", "t1contrast"),
    "flair": ("flair", "t2flair"),
    "dwi": (
        "dwi",
        "diffusion",
        "diffusionweighted",
        "diffusionweightedimaging",
        "adc",
    ),
}


@dataclass(frozen=True)
class Stage8PatientAudit:
    patient_id: int
    exposed_development: bool
    core_eligible: bool
    complete_rt_schedule: bool
    rtdose_available: bool
    gtv_complete: bool
    required_modalities_complete: bool
    flair_t0_t1_complete: bool
    dwi_t0_t1_complete: bool
    rt_total_dose_gy: float | None
    rt_fractions: int | None
    model_tier: str
    split_stratum: str
    split: str
    missing_requirements: tuple[str, ...]
    availability: dict[str, bool]


@dataclass(frozen=True)
class Stage8DataAuditResult:
    directory: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class _ProvisionalPatient:
    patient_id: int
    exposed: bool
    core_eligible: bool
    complete_rt: bool
    rtdose: bool
    gtv_complete: bool
    required_complete: bool
    flair_t0_t1: bool
    dwi_t0_t1: bool
    rt_total_dose_gy: float | None
    rt_fractions: int | None
    model_tier: str
    split_stratum: str
    missing: tuple[str, ...]
    availability: dict[str, bool]


def _latest_single(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))

    if not matches:
        raise FileNotFoundError(
            f"No metadata file matches {pattern!r} in {root}"
        )

    return matches[-1]


def _normalize_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def _find_modality_column(
    columns: list[str],
    modality: str,
) -> str | None:
    normalized = {
        _normalize_column(column): column
        for column in columns
    }

    for alias in _MODALITY_ALIASES.get(modality, (modality,)):
        match = normalized.get(_normalize_column(alias))

        if match is not None:
            return match

    return None


def _availability_value(value: object) -> bool:
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return float(value) == 1.0

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "available",
    }


def _modality_available(
    mri: pd.DataFrame,
    *,
    patient_id: int,
    timepoint: str,
    column: str | None,
) -> bool:
    if column is None:
        return False

    rows = mri[
        (mri["id_patient"] == patient_id)
        & (
            mri["temporality"].astype(str).str.lower()
            == timepoint.lower()
        )
    ]

    if rows.empty:
        return False

    return any(
        _availability_value(value)
        for value in rows[column].tolist()
    )


def _split_rank(seed: int, patient_id: int) -> str:
    return hashlib.sha256(
        f"stage8:{seed}:{patient_id}".encode("ascii")
    ).hexdigest()


def _stratified_holdout(
    patients: list[_ProvisionalPatient],
    *,
    fraction: float,
    seed: int,
) -> set[int]:
    by_stratum: dict[str, list[int]] = {}

    for patient in patients:
        if not patient.core_eligible or patient.exposed:
            continue

        by_stratum.setdefault(patient.split_stratum, []).append(
            patient.patient_id
        )

    selected: set[int] = set()

    for stratum, patient_ids in sorted(by_stratum.items()):
        ordered = sorted(
            patient_ids,
            key=lambda patient_id: hashlib.sha256(
                (
                    f"stage8:{seed}:{stratum}:{patient_id}"
                ).encode("utf-8")
            ).hexdigest(),
        )
        raw_count = len(ordered) * fraction
        count = int(round(raw_count))

        # Do not consume the only patient in a rare stratum. For strata with
        # enough support, reserve at least one and leave at least one for
        # development/model selection.
        if len(ordered) >= 2:
            count = min(len(ordered) - 1, max(1, count))
        else:
            count = 0

        selected.update(ordered[:count])

    return selected


def _model_tier(
    *,
    core_eligible: bool,
    flair_t0_t1_complete: bool,
    dwi_t0_t1_complete: bool,
) -> str:
    if not core_eligible:
        return "ineligible"

    if flair_t0_t1_complete and dwi_t0_t1_complete:
        return "mpmri"

    if flair_t0_t1_complete:
        return "t1gd-flair"

    return "t1gd-only"


def _rt_regimen_label(fractions: int | None) -> str:
    if fractions is None:
        return "rt-unknown"

    if fractions <= 20:
        return "rt-hypofractionated"

    return "rt-conventional"


def _patient_rows(
    *,
    mri: pd.DataFrame,
    treatment: CFBTreatmentMetadata,
    config: Stage8ProtocolConfig,
) -> list[Stage8PatientAudit]:
    if "id_patient" not in mri.columns or "temporality" not in mri.columns:
        raise ValueError(
            "MRI availability metadata must contain id_patient and temporality"
        )

    modalities = tuple(
        dict.fromkeys(
            (*config.required_modalities, *config.preferred_modalities)
        )
    )
    modality_columns = {
        modality: _find_modality_column(
            [str(column) for column in mri.columns],
            modality,
        )
        for modality in modalities
    }
    patient_ids = sorted(
        int(value)
        for value in mri["id_patient"].dropna().unique().tolist()
    )
    exposed_ids = set(config.exposed_development_patient_ids)
    provisional: list[_ProvisionalPatient] = []

    for patient_id in patient_ids:
        availability: dict[str, bool] = {}

        for timepoint in config.required_timepoints:
            for modality in modalities:
                key = f"{timepoint}_{modality}"
                availability[key] = _modality_available(
                    mri,
                    patient_id=patient_id,
                    timepoint=timepoint,
                    column=modality_columns[modality],
                )

        imaging_records = treatment.imaging_records(patient_id)
        imaging_by_timepoint = {
            record.temporality.lower(): record
            for record in imaging_records
        }

        for timepoint in config.required_timepoints:
            record = imaging_by_timepoint.get(timepoint.lower())
            availability[f"{timepoint}_gtv"] = bool(
                record is not None and record.gtv_available
            )

        required_complete = all(
            availability[f"{timepoint}_{modality}"]
            for timepoint in config.required_timepoints
            for modality in config.required_modalities
        )
        gtv_complete = all(
            availability[f"{timepoint}_gtv"]
            for timepoint in config.required_timepoints
        )
        flair_t0_t1 = all(
            availability.get(f"{timepoint}_flair", False)
            for timepoint in ("t0", "t1")
        )
        dwi_t0_t1 = all(
            availability.get(f"{timepoint}_dwi", False)
            for timepoint in ("t0", "t1")
        )

        treatment_record = treatment.treatment(patient_id)
        complete_rt = bool(
            treatment_record is not None
            and treatment_record.radiotherapy_start_day is not None
            and treatment_record.dose_gy is not None
            and treatment_record.fractions_number is not None
            and treatment_record.dose_gy > 0.0
            and treatment_record.fractions_number > 0
        )
        rt_total_dose_gy = (
            None if treatment_record is None else treatment_record.dose_gy
        )
        rt_fractions = (
            None
            if treatment_record is None
            else treatment_record.fractions_number
        )
        rtdose = any(record.rtdose_available for record in imaging_records)

        missing: list[str] = []

        for timepoint in config.required_timepoints:
            for modality in config.required_modalities:
                key = f"{timepoint}_{modality}"

                if not availability[key]:
                    missing.append(key)

            if not availability[f"{timepoint}_gtv"]:
                missing.append(f"{timepoint}_gtv")

        if config.require_complete_rt_schedule and not complete_rt:
            missing.append("complete_rt_schedule")

        if config.require_rtdose and not rtdose:
            missing.append("rtdose")

        core_eligible = not missing
        tier = _model_tier(
            core_eligible=core_eligible,
            flair_t0_t1_complete=flair_t0_t1,
            dwi_t0_t1_complete=dwi_t0_t1,
        )
        stratum = f"{tier}:{_rt_regimen_label(rt_fractions)}"

        provisional.append(
            _ProvisionalPatient(
                patient_id=patient_id,
                exposed=patient_id in exposed_ids,
                core_eligible=core_eligible,
                complete_rt=complete_rt,
                rtdose=rtdose,
                gtv_complete=gtv_complete,
                required_complete=required_complete,
                flair_t0_t1=flair_t0_t1,
                dwi_t0_t1=dwi_t0_t1,
                rt_total_dose_gy=rt_total_dose_gy,
                rt_fractions=rt_fractions,
                model_tier=tier,
                split_stratum=stratum,
                missing=tuple(missing),
                availability=availability,
            )
        )

    holdout_ids = _stratified_holdout(
        provisional,
        fraction=config.holdout_fraction,
        seed=config.split_seed,
    )
    rows: list[Stage8PatientAudit] = []

    for patient in provisional:
        if not patient.core_eligible:
            split = "ineligible"
        elif patient.exposed:
            split = "development-exposed"
        elif patient.patient_id in holdout_ids:
            split = "untouched-holdout"
        else:
            split = "development"

        rows.append(
            Stage8PatientAudit(
                patient_id=patient.patient_id,
                exposed_development=patient.exposed,
                core_eligible=patient.core_eligible,
                complete_rt_schedule=patient.complete_rt,
                rtdose_available=patient.rtdose,
                gtv_complete=patient.gtv_complete,
                required_modalities_complete=patient.required_complete,
                flair_t0_t1_complete=patient.flair_t0_t1,
                dwi_t0_t1_complete=patient.dwi_t0_t1,
                rt_total_dose_gy=patient.rt_total_dose_gy,
                rt_fractions=patient.rt_fractions,
                model_tier=patient.model_tier,
                split_stratum=patient.split_stratum,
                split=split,
                missing_requirements=patient.missing,
                availability=patient.availability,
            )
        )

    return rows


def _write_csv(path: Path, rows: list[Stage8PatientAudit]) -> None:
    availability_columns = sorted(
        {key for row in rows for key in row.availability}
    )
    columns = [
        "patient_id",
        "split",
        "split_stratum",
        "model_tier",
        "exposed_development",
        "core_eligible",
        "complete_rt_schedule",
        "rt_total_dose_gy",
        "rt_fractions",
        "rtdose_available",
        "gtv_complete",
        "required_modalities_complete",
        "flair_t0_t1_complete",
        "dwi_t0_t1_complete",
        "missing_requirements",
        *availability_columns,
    ]

    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=columns,
            lineterminator="\n",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    "patient_id": row.patient_id,
                    "split": row.split,
                    "split_stratum": row.split_stratum,
                    "model_tier": row.model_tier,
                    "exposed_development": row.exposed_development,
                    "core_eligible": row.core_eligible,
                    "complete_rt_schedule": row.complete_rt_schedule,
                    "rt_total_dose_gy": row.rt_total_dose_gy,
                    "rt_fractions": row.rt_fractions,
                    "rtdose_available": row.rtdose_available,
                    "gtv_complete": row.gtv_complete,
                    "required_modalities_complete": (
                        row.required_modalities_complete
                    ),
                    "flair_t0_t1_complete": row.flair_t0_t1_complete,
                    "dwi_t0_t1_complete": row.dwi_t0_t1_complete,
                    "missing_requirements": ";".join(
                        row.missing_requirements
                    ),
                    **row.availability,
                }
            )


def audit_stage8_cohort(
    *,
    metadata_root: Path,
    protocol_config_path: Path,
    output_dir: Path,
) -> Stage8DataAuditResult:
    destination = output_dir.resolve()

    if destination.exists():
        raise FileExistsError(
            f"Stage 8 data-audit destination already exists: {destination}"
        )

    config = load_stage8_protocol_config(protocol_config_path)
    metadata_root = metadata_root.resolve()
    mri_path = _latest_single(
        metadata_root,
        "CFB-GBM_mri_availability_*.tsv",
    )
    treatment_path = _latest_single(
        metadata_root,
        "CFB-GBM_treatment_data_*.tsv",
    )
    treatment_imaging_path = _latest_single(
        metadata_root,
        "CFB-GBM_treatment_imaging_availability_*.tsv",
    )

    # Deliberately do not open RANO metadata. Split assignment uses only
    # availability and treatment-plan metadata, never outcome values.
    mri = pd.read_csv(mri_path, sep="\t")
    treatment = CFBTreatmentMetadata(metadata_root)
    rows = _patient_rows(
        mri=mri,
        treatment=treatment,
        config=config,
    )

    eligible = [row for row in rows if row.core_eligible]
    development = [
        row.patient_id
        for row in rows
        if row.split in {"development", "development-exposed"}
    ]
    holdout = [
        row.patient_id
        for row in rows
        if row.split == "untouched-holdout"
    ]
    tier_counts: dict[str, int] = {}
    stratum_counts: dict[str, int] = {}

    for row in eligible:
        tier_counts[row.model_tier] = tier_counts.get(row.model_tier, 0) + 1
        stratum_counts[row.split_stratum] = (
            stratum_counts.get(row.split_stratum, 0) + 1
        )

    manifest: dict[str, object] = {
        "schema_version": STAGE8_DATA_AUDIT_SCHEMA_VERSION,
        "kind": "stage8_multimodal_data_audit",
        "sealed": True,
        "protocol_config_sha256": sha256_file(
            protocol_config_path.resolve()
        ),
        "metadata_sha256": {
            path.name: sha256_file(path)
            for path in (
                mri_path,
                treatment_path,
                treatment_imaging_path,
            )
        },
        "leakage_control": {
            "rano_metadata_loaded": False,
            "t2_image_content_loaded": False,
            "split_uses_outcomes": False,
            "split_inputs": [
                "MRI availability metadata",
                "GTV availability metadata",
                "RT schedule completeness",
                "RTDOSE availability",
                "explicit exposed-development patient IDs",
            ],
        },
        "summary": {
            "patient_count": len(rows),
            "core_eligible_count": len(eligible),
            "development_count": len(development),
            "untouched_holdout_count": len(holdout),
            "exposed_development_count": sum(
                row.exposed_development for row in rows
            ),
            "rtdose_available_count": sum(
                row.rtdose_available for row in rows
            ),
            "gtv_complete_count": sum(row.gtv_complete for row in rows),
            "flair_t0_t1_complete_count": sum(
                row.flair_t0_t1_complete for row in rows
            ),
            "dwi_t0_t1_complete_count": sum(
                row.dwi_t0_t1_complete for row in rows
            ),
            "model_tier_counts": tier_counts,
            "split_stratum_counts": stratum_counts,
        },
        "split": {
            "method": "deterministic_stratified_hash_v1",
            "seed": config.split_seed,
            "holdout_fraction": config.holdout_fraction,
            "stratification": ["model_tier", "rt_regimen"],
            "development_patient_ids": sorted(development),
            "untouched_holdout_patient_ids": sorted(holdout),
        },
        "patients": [asdict(row) for row in rows],
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )

    try:
        manifest_path = temporary / "stage8_data_audit.json"
        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (temporary / "stage8_data_audit.sha256").write_text(
            sha256_file(manifest_path) + "  stage8_data_audit.json\n",
            encoding="ascii",
        )
        _write_csv(temporary / "stage8_data_audit.csv", rows)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return load_sealed_stage8_data_audit(destination)


def load_sealed_stage8_data_audit(directory: Path) -> Stage8DataAuditResult:
    root = directory.resolve()
    manifest_path = root / "stage8_data_audit.json"
    seal_path = root / "stage8_data_audit.sha256"

    if not manifest_path.is_file() or not seal_path.is_file():
        raise FileNotFoundError("Stage 8 data-audit artifact is incomplete")

    tokens = seal_path.read_text(encoding="ascii").split()

    if not tokens or sha256_file(manifest_path) != tokens[0]:
        raise ValueError("Stage 8 data-audit checksum mismatch")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Stage 8 data audit must contain a JSON object")

    payload = cast(dict[str, object], raw)

    if payload.get("schema_version") != STAGE8_DATA_AUDIT_SCHEMA_VERSION:
        raise ValueError("Unsupported Stage 8 data-audit schema version")

    if payload.get("kind") != "stage8_multimodal_data_audit":
        raise ValueError("Artifact is not a Stage 8 multimodal data audit")

    if payload.get("sealed") is not True:
        raise ValueError("Stage 8 data audit is not sealed")

    leakage = payload.get("leakage_control")

    if not isinstance(leakage, dict):
        raise ValueError("Stage 8 leakage-control metadata is missing")

    if leakage.get("split_uses_outcomes") is not False:
        raise ValueError("Stage 8 split violates leakage-control contract")

    return Stage8DataAuditResult(directory=root, manifest=payload)
