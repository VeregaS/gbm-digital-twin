from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_inputs import discover_patient_rtdose_path
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)

MaterializationMode = Literal["auto", "hardlink", "copy"]


@dataclass(frozen=True)
class Stage8MaterializationItem:
    patient_id: int
    input_name: str
    source_path: Path
    destination_path: Path


@dataclass(frozen=True)
class Stage8MaterializationResult:
    source_root: Path
    destination_root: Path
    patient_ids: tuple[int, ...]
    required_count: int
    created_count: int
    reused_count: int
    hardlink_count: int
    copy_count: int
    dry_run: bool


def _internal_validation_patient_ids(
    manifest: dict[str, object],
) -> tuple[int, ...]:
    raw_patients = manifest.get("patients")
    if not isinstance(raw_patients, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    selected: list[int] = []
    for raw in raw_patients:
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")

        if raw.get("split") not in {"development", "internal-validation"}:
            continue
        if raw.get("core_eligible") is not True:
            continue
        if raw.get("exposed_development") is True:
            continue

        patient_id = raw.get("patient_id")
        if type(patient_id) is not int:
            raise ValueError("Stage 8 audit patient_id must be an integer")
        selected.append(patient_id)

    result = tuple(sorted(selected))
    if not result:
        raise ValueError(
            "Stage 8 audit contains no internal-validation patients"
        )
    return result


def _core_source_items(
    source_root: Path,
    destination_root: Path,
    *,
    patient_id: int,
) -> list[Stage8MaterializationItem]:
    items: list[Stage8MaterializationItem] = []

    for timepoint in ("t0", "t1", "t2"):
        source_dir = source_root / str(patient_id) / timepoint
        destination_dir = destination_root / str(patient_id) / timepoint
        prefix = f"{patient_id}_{timepoint}"

        for suffix, label in (
            ("t1gd", "T1Gd"),
            ("gtv", "GTV"),
            ("brain_mask", "brain mask"),
        ):
            filename = f"{prefix}_{suffix}.nii.gz"
            items.append(
                Stage8MaterializationItem(
                    patient_id=patient_id,
                    input_name=f"{timepoint} {label}",
                    source_path=source_dir / filename,
                    destination_path=destination_dir / filename,
                )
            )

    return items


def build_stage8_materialization_plan(
    *,
    source_root: Path,
    destination_root: Path,
    patient_ids: tuple[int, ...],
    require_spatial_rtdose: bool,
) -> tuple[Stage8MaterializationItem, ...]:
    source = source_root.resolve()
    destination = destination_root.resolve()
    items: list[Stage8MaterializationItem] = []

    for patient_id in patient_ids:
        items.extend(
            _core_source_items(
                source,
                destination,
                patient_id=patient_id,
            )
        )

        if require_spatial_rtdose:
            dose = discover_patient_rtdose_path(
                patients_root=source,
                patient_id=patient_id,
            )
            if dose is None:
                expected = source / str(patient_id) / "**" / "*rtdose*.nii.gz"
                items.append(
                    Stage8MaterializationItem(
                        patient_id=patient_id,
                        input_name="RTDOSE",
                        source_path=expected,
                        destination_path=(
                            destination
                            / str(patient_id)
                            / "rt"
                            / f"{patient_id}_rtdose.nii.gz"
                        ),
                    )
                )
            else:
                items.append(
                    Stage8MaterializationItem(
                        patient_id=patient_id,
                        input_name="RTDOSE",
                        source_path=dose,
                        destination_path=(
                            destination
                            / str(patient_id)
                            / "rt"
                            / dose.name
                        ),
                    )
                )

    return tuple(items)


def _source_issues(
    items: tuple[Stage8MaterializationItem, ...],
) -> tuple[Stage8MaterializationItem, ...]:
    return tuple(
        item
        for item in items
        if not item.source_path.is_file()
        or item.source_path.stat().st_size <= 0
    )


def _source_error(
    source_root: Path,
    issues: tuple[Stage8MaterializationItem, ...],
) -> str:
    preview_limit = 40
    patient_count = len({item.patient_id for item in issues})
    lines = [
        (
            "Stage 8 source-data preflight failed; no destination files "
            "were created."
        ),
        f"Source data root: {source_root}",
        (
            f"Missing source inputs: {len(issues)} across "
            f"{patient_count} patients."
        ),
        (
            "Expected the official CFB-GBM NIfTI data tree "
            "<source>/<patient>/<t0|t1|t2>/..."
        ),
    ]

    for item in issues[:preview_limit]:
        lines.append(
            f"  patient {item.patient_id}: {item.input_name} -> "
            f"{item.source_path}"
        )

    remaining = len(issues) - preview_limit
    if remaining > 0:
        lines.append(f"  ... and {remaining} more missing source inputs")

    return "\n".join(lines)


def _same_existing_file(
    source: Path,
    destination: Path,
) -> bool:
    if not destination.is_file():
        return False

    source_size = source.stat().st_size
    destination_size = destination.stat().st_size
    if source_size != destination_size:
        raise ValueError(
            "Existing Stage 8 destination has a different size: "
            f"{destination}"
        )

    try:
        if source.samefile(destination):
            return True
    except OSError:
        pass

    if sha256_file(source) != sha256_file(destination):
        raise ValueError(
            "Existing Stage 8 destination differs from the official source: "
            f"{destination}"
        )

    return True


def _materialize_one(
    source: Path,
    destination: Path,
    *,
    mode: MaterializationMode,
) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.{os.getpid()}.tmp"
    )

    if temporary.exists():
        temporary.unlink()

    try:
        if mode in {"auto", "hardlink"}:
            try:
                os.link(source, temporary)
            except OSError:
                if mode == "hardlink":
                    raise
            else:
                temporary.replace(destination)
                return "hardlink"

        shutil.copy2(source, temporary)
        temporary.replace(destination)
        return "copy"
    finally:
        if temporary.exists():
            temporary.unlink()


def resolve_stage8_source_data_root(
    *,
    explicit: Path | None,
    patients_root: Path,
) -> Path:
    if explicit is not None:
        return explicit.resolve()

    environment = os.getenv("GBM_TWIN_CFB_SOURCE_DATA_ROOT")
    if environment:
        return Path(environment).resolve()

    cfb_root = os.getenv("GBM_TWIN_CFB_ROOT")
    if cfb_root:
        return (Path(cfb_root) / "data").resolve()

    return (patients_root.resolve().parent / "data").resolve()


def materialize_stage8_internal_validation(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    data_audit_root: Path,
    selection_root: Path,
    source_data_root: Path | None = None,
    mode: MaterializationMode = "auto",
    dry_run: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Stage8MaterializationResult:
    if mode not in {"auto", "hardlink", "copy"}:
        raise ValueError(f"Unsupported materialization mode: {mode}")

    audit = load_sealed_stage8_data_audit(data_audit_root)
    selected = load_selected_stage8_model(selection_root)
    audit_sha = sha256_file(
        data_audit_root.resolve() / "stage8_data_audit.json"
    )

    if selected.stage8_data_audit_sha256 != audit_sha:
        raise ValueError(
            "Selected Stage 8 model does not match the sealed data audit"
        )

    experiment = load_cohort_experiment_config(experiment_config_path)
    patients_root = (
        experiment.patients_root
        if experiment.patients_root.is_absolute()
        else repo_root.resolve() / experiment.patients_root
    ).resolve()
    source_root = resolve_stage8_source_data_root(
        explicit=source_data_root,
        patients_root=patients_root,
    )

    if not source_root.is_dir():
        raise FileNotFoundError(
            "Official CFB-GBM NIfTI data directory was not found: "
            f"{source_root}\n"
            "Download/extract the TCIA CFB-GBM NIfTI package so this "
            "directory contains <patient>/<temporality> folders, or pass "
            "--source-data-root explicitly."
        )

    patient_ids = _internal_validation_patient_ids(audit.manifest)
    items = build_stage8_materialization_plan(
        source_root=source_root,
        destination_root=patients_root,
        patient_ids=patient_ids,
        require_spatial_rtdose=selected.candidate.use_spatial_rtdose,
    )
    issues = _source_issues(items)
    if issues:
        raise FileNotFoundError(_source_error(source_root, issues))

    if progress is not None:
        progress(
            f"[stage8-materialize] source preflight passed: "
            f"{len(items)} inputs for {len(patient_ids)} patients"
        )

    created = 0
    reused = 0
    hardlinks = 0
    copies = 0

    for index, item in enumerate(items, start=1):
        if _same_existing_file(item.source_path, item.destination_path):
            reused += 1
            action = "reused"
        elif dry_run:
            action = "planned"
        else:
            action = _materialize_one(
                item.source_path,
                item.destination_path,
                mode=mode,
            )
            created += 1
            if action == "hardlink":
                hardlinks += 1
            elif action == "copy":
                copies += 1

        if progress is not None:
            progress(
                f"[stage8-materialize] {index}/{len(items)} "
                f"patient={item.patient_id} {item.input_name}: {action}"
            )

    return Stage8MaterializationResult(
        source_root=source_root,
        destination_root=patients_root,
        patient_ids=patient_ids,
        required_count=len(items),
        created_count=created,
        reused_count=reused,
        hardlink_count=hardlinks,
        copy_count=copies,
        dry_run=dry_run,
    )
