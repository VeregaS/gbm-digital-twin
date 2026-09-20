from __future__ import annotations

import csv
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)

MPMRI_AUDIT_SCHEMA_VERSION = 1
TIMEPOINTS = ("t0", "t1", "t2")
MODALITY_ALIASES: dict[str, tuple[str, ...]] = {
    "t1gd": ("t1gd", "t1eg", "t1ce"),
    "gtv": ("gtv",),
    "brain_mask": ("brain_mask", "brainmask"),
    "flair": ("flair", "t2f"),
    "adc": ("adc",),
    "dwi": ("dwi", "diffusion"),
}


@dataclass(frozen=True)
class MPMRIPatientAuditRow:
    patient_id: int
    split: str
    exposed_development: bool
    t0_t1gd: bool
    t0_flair: bool
    t0_adc: bool
    t0_dwi: bool
    t1_t1gd: bool
    t1_flair: bool
    t1_adc: bool
    t1_dwi: bool
    t2_t1gd: bool
    t2_flair: bool
    t2_adc: bool
    t2_dwi: bool
    longitudinal_t1gd: bool
    longitudinal_flair: bool
    longitudinal_adc: bool
    longitudinal_dwi: bool
    longitudinal_t1gd_flair: bool
    longitudinal_t1gd_adc: bool
    local_patient_directory: bool


@dataclass(frozen=True)
class MPMRIAuditArtifact:
    directory: Path
    manifest: dict[str, object]


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return cast(dict[str, object], value)


def _patient_rows(
    audit_manifest: dict[str, object],
) -> list[dict[str, object]]:
    raw = audit_manifest.get("patients")
    if not isinstance(raw, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    result: list[dict[str, object]] = []
    for item in raw:
        result.append(_mapping(item, name="Stage 8 audit patient row"))
    return result


def _patient_id(row: dict[str, object]) -> int:
    value = row.get("patient_id")
    if type(value) is not int:
        raise ValueError("Stage 8 audit patient_id must be integer")
    return cast(int, value)


def _modality_present(
    patient_root: Path,
    *,
    patient_id: int,
    timepoint: str,
    modality: str,
) -> bool:
    aliases = MODALITY_ALIASES[modality]
    timepoint_root = patient_root / timepoint
    if not timepoint_root.is_dir():
        return False

    expected_stems = {
        f"{patient_id}_{timepoint}_{alias}".lower()
        for alias in aliases
    }
    for path in timepoint_root.iterdir():
        if not path.is_file():
            continue
        name = path.name.lower()
        if name.endswith(".nii.gz"):
            stem = name[:-7]
        elif name.endswith(".nii"):
            stem = name[:-4]
        else:
            continue
        if stem in expected_stems:
            return True
    return False


def audit_local_mpmri(
    *,
    repo_root: Path,
    data_audit_root: Path,
    experiment_config_path: Path,
    output_dir: Path,
) -> MPMRIAuditArtifact:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"mpMRI audit destination already exists: {destination}"
        )

    audit = load_sealed_stage8_data_audit(data_audit_root)
    audit_sha = sha256_file(
        data_audit_root.resolve() / "stage8_data_audit.json"
    )
    experiment = load_cohort_experiment_config(experiment_config_path)
    patients_root = (
        experiment.patients_root
        if experiment.patients_root.is_absolute()
        else repo_root.resolve() / experiment.patients_root
    )

    rows: list[MPMRIPatientAuditRow] = []
    for source_row in _patient_rows(audit.manifest):
        patient_id = _patient_id(source_row)
        patient_root = patients_root / str(patient_id)
        presence: dict[tuple[str, str], bool] = {}

        for timepoint in TIMEPOINTS:
            for modality in MODALITY_ALIASES:
                presence[(timepoint, modality)] = _modality_present(
                    patient_root,
                    patient_id=patient_id,
                    timepoint=timepoint,
                    modality=modality,
                )

        rows.append(
            MPMRIPatientAuditRow(
                patient_id=patient_id,
                split=str(source_row.get("split", "")),
                exposed_development=(
                    source_row.get("exposed_development") is True
                ),
                t0_t1gd=presence[("t0", "t1gd")],
                t0_flair=presence[("t0", "flair")],
                t0_adc=presence[("t0", "adc")],
                t0_dwi=presence[("t0", "dwi")],
                t1_t1gd=presence[("t1", "t1gd")],
                t1_flair=presence[("t1", "flair")],
                t1_adc=presence[("t1", "adc")],
                t1_dwi=presence[("t1", "dwi")],
                t2_t1gd=presence[("t2", "t1gd")],
                t2_flair=presence[("t2", "flair")],
                t2_adc=presence[("t2", "adc")],
                t2_dwi=presence[("t2", "dwi")],
                longitudinal_t1gd=all(
                    presence[(timepoint, "t1gd")]
                    for timepoint in TIMEPOINTS
                ),
                longitudinal_flair=all(
                    presence[(timepoint, "flair")]
                    for timepoint in TIMEPOINTS
                ),
                longitudinal_adc=all(
                    presence[(timepoint, "adc")]
                    for timepoint in TIMEPOINTS
                ),
                longitudinal_dwi=all(
                    presence[(timepoint, "dwi")]
                    for timepoint in TIMEPOINTS
                ),
                longitudinal_t1gd_flair=all(
                    presence[(timepoint, modality)]
                    for timepoint in TIMEPOINTS
                    for modality in ("t1gd", "flair")
                ),
                longitudinal_t1gd_adc=all(
                    presence[(timepoint, modality)]
                    for timepoint in TIMEPOINTS
                    for modality in ("t1gd", "adc")
                ),
                local_patient_directory=patient_root.is_dir(),
            )
        )

    def count(attribute: str) -> int:
        return sum(bool(getattr(row, attribute)) for row in rows)

    payload: dict[str, object] = {
        "schema_version": MPMRI_AUDIT_SCHEMA_VERSION,
        "kind": "local_mpmri_availability_audit",
        "source": {
            "stage8_data_audit_sha256": audit_sha,
            "experiment_config_sha256": sha256_file(
                experiment_config_path.resolve()
            ),
            "patients_root": str(patients_root),
        },
        "summary": {
            "patient_count": len(rows),
            "local_patient_directory_count": count(
                "local_patient_directory"
            ),
            "longitudinal_t1gd_count": count("longitudinal_t1gd"),
            "longitudinal_flair_count": count("longitudinal_flair"),
            "longitudinal_adc_count": count("longitudinal_adc"),
            "longitudinal_dwi_count": count("longitudinal_dwi"),
            "longitudinal_t1gd_flair_count": count(
                "longitudinal_t1gd_flair"
            ),
            "longitudinal_t1gd_adc_count": count(
                "longitudinal_t1gd_adc"
            ),
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
        manifest_path = temporary / "mpmri_availability.json"
        manifest_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        fieldnames = list(asdict(rows[0]).keys()) if rows else []
        with (
            temporary / "mpmri_availability.csv"
        ).open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=fieldnames,
                lineterminator="\n",
            )
            if rows:
                writer.writeheader()
                for row in rows:
                    writer.writerow(asdict(row))
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return MPMRIAuditArtifact(
        directory=destination,
        manifest=payload,
    )
