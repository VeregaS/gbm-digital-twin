from __future__ import annotations

import csv
import json
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import numpy as np

from gbm_twin.evaluation.error_analysis import (
    CohortPatientErrorRecord,
    classify_volume_trajectory,
    relative_volume_change,
    summarize_error_records,
)
from gbm_twin.evaluation.error_analysis_config import (
    CohortErrorAnalysisConfig,
    load_cohort_error_analysis_config,
)
from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationPayload,
    PatientEvaluationPayload,
)
from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.patient_catalog import (
    get_patient_catalog_summary,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
    prepare_patient_timepoint,
)
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.twin_artifacts import (
    load_frozen_patient_artifact,
    target_spacing,
)
from gbm_twin.workflows.twin_qc import get_twin_patient_qc

COHORT_ERROR_ANALYSIS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CohortErrorAnalysisResult:
    directory: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class _CalibrationSnapshot:
    diffusion: float
    proliferation: float
    dice: float
    volume_error: float
    loss: float
    identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool


def _require_mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(
            f"Prediction manifest field {key!r} must be a mapping"
        )
    return cast(dict[str, object], value)


def _require_float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"Prediction manifest field {key!r} must be numeric"
        )
    return float(value)


def _require_bool(
    mapping: dict[str, object],
    key: str,
) -> bool:
    value = mapping.get(key)
    if type(value) is not bool:
        raise ValueError(
            f"Prediction manifest field {key!r} must be boolean"
        )
    return cast(bool, value)


def _calibration_snapshot(
    manifest: dict[str, object],
) -> _CalibrationSnapshot:
    parameters = _require_mapping(manifest, "parameters")
    calibration = _require_mapping(manifest, "calibration")
    best = _require_mapping(calibration, "best")
    diagnostics = _require_mapping(calibration, "diagnostics")

    return _CalibrationSnapshot(
        diffusion=_require_float(parameters, "diffusion"),
        proliferation=_require_float(parameters, "proliferation"),
        dice=_require_float(best, "dice"),
        volume_error=_require_float(best, "volume_error"),
        loss=_require_float(best, "loss"),
        identifiable=_require_bool(diagnostics, "identifiable"),
        diffusion_at_boundary=_require_bool(
            diagnostics,
            "diffusion_at_boundary",
        ),
        proliferation_at_boundary=_require_bool(
            diagnostics,
            "proliferation_at_boundary",
        ),
    )


def _gtv_volume_cm3(
    prepared: PreparedPatientTimepoint,
) -> float:
    mask = np.asarray(prepared.gtv.data) > 0.5
    voxel_volume_cm3 = float(np.prod(prepared.spacing)) / 1000.0
    return float(np.count_nonzero(mask)) * voxel_volume_cm3


def _patient_record(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    patient: PatientEvaluationPayload,
    evaluation_payload: CohortEvaluationPayload,
    spacing: tuple[float, float, float],
    config: CohortErrorAnalysisConfig,
) -> CohortPatientErrorRecord:
    patient_id = patient["patient_id"]
    catalog = get_patient_catalog_summary(
        metadata_root=metadata_root,
        patient_id=patient_id,
    )

    prepared_by_name = {
        name: prepare_patient_timepoint(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=name,
            target_spacing=spacing,
        )
        for name in ("t0", "t1", "t2")
    }

    volume_t0 = _gtv_volume_cm3(prepared_by_name["t0"])
    volume_t1 = _gtv_volume_cm3(prepared_by_name["t1"])
    volume_t2 = _gtv_volume_cm3(prepared_by_name["t2"])

    change_t0_t1 = relative_volume_change(volume_t0, volume_t1)
    change_t1_t2 = relative_volume_change(volume_t1, volume_t2)

    artifact = load_frozen_patient_artifact(
        cohort_freeze_root=cohort_freeze_root,
        payload=evaluation_payload,
        patient_id=patient_id,
    )
    calibration = _calibration_snapshot(
        cast(dict[str, object], artifact.manifest)
    )

    qc = get_twin_patient_qc(
        metadata_root=metadata_root,
        patients_root=patients_root,
        cohort_freeze_root=cohort_freeze_root,
        cohort_evaluation_root=cohort_evaluation_root,
        patient_id=patient_id,
    )

    twin = patient["twin"]
    persistence = patient["persistence"]
    volume_baseline = patient["volume_baseline"]

    twin_dice = twin["dice"]
    persistence_dice = persistence["dice"]
    volume_baseline_dice = volume_baseline["dice"]

    return CohortPatientErrorRecord(
        patient_id=patient_id,
        calibration_days=catalog.dt01_days,
        forecast_horizon_days=catalog.dt12_days,
        target_day=patient["target_day"],
        rt_start_day=catalog.treatment.rt_start_day,
        rt_started_by_t1=catalog.treatment.rt_started_by_t1,
        treatment_reconstructable=catalog.treatment.reconstructable,
        volume_t0_cm3=volume_t0,
        volume_t1_cm3=volume_t1,
        volume_t2_cm3=volume_t2,
        volume_change_t0_t1=change_t0_t1,
        volume_change_t1_t2=change_t1_t2,
        trajectory_t0_t1=classify_volume_trajectory(
            change_t0_t1,
            stable_threshold=config.stable_volume_change_fraction,
        ),
        trajectory_t1_t2=classify_volume_trajectory(
            change_t1_t2,
            stable_threshold=config.stable_volume_change_fraction,
        ),
        diffusion=calibration.diffusion,
        proliferation=calibration.proliferation,
        calibration_dice=calibration.dice,
        calibration_volume_error=calibration.volume_error,
        calibration_loss=calibration.loss,
        calibration_identifiable=calibration.identifiable,
        diffusion_at_boundary=calibration.diffusion_at_boundary,
        proliferation_at_boundary=calibration.proliferation_at_boundary,
        twin_dice=twin_dice,
        twin_volume_error=twin["relative_volume_error"],
        twin_hd95_mm=twin["hd95_mm"],
        twin_centroid_distance_mm=twin["centroid_distance_mm"],
        persistence_dice=persistence_dice,
        persistence_volume_error=persistence["relative_volume_error"],
        volume_baseline_dice=volume_baseline_dice,
        volume_baseline_volume_error=(
            volume_baseline["relative_volume_error"]
        ),
        twin_minus_persistence_dice=(
            twin_dice - persistence_dice
        ),
        twin_minus_volume_baseline_dice=(
            twin_dice - volume_baseline_dice
        ),
        qc_warning_codes=tuple(
            warning.code.value
            for warning in qc.warnings
        ),
        observed_outside_brain_fraction=(
            qc.observed.outside_brain_fraction
        ),
        twin_outside_brain_fraction=(
            qc.twin.outside_brain_fraction
        ),
        observed_component_count=qc.observed.component_count,
        twin_component_count=qc.twin.component_count,
        observed_largest_component_fraction=(
            qc.observed.largest_component_fraction
        ),
        twin_largest_component_fraction=(
            qc.twin.largest_component_fraction
        ),
    )


_CSV_COLUMNS = (
    "patient_id",
    "calibration_days",
    "forecast_horizon_days",
    "volume_t0_cm3",
    "volume_t1_cm3",
    "volume_t2_cm3",
    "volume_change_t0_t1",
    "volume_change_t1_t2",
    "trajectory_t0_t1",
    "trajectory_t1_t2",
    "diffusion",
    "proliferation",
    "calibration_dice",
    "calibration_volume_error",
    "calibration_loss",
    "calibration_identifiable",
    "diffusion_at_boundary",
    "proliferation_at_boundary",
    "twin_dice",
    "persistence_dice",
    "volume_baseline_dice",
    "twin_minus_persistence_dice",
    "twin_minus_volume_baseline_dice",
    "twin_volume_error",
    "twin_hd95_mm",
    "twin_centroid_distance_mm",
    "qc_warning_count",
    "qc_warning_codes",
    "observed_outside_brain_fraction",
    "twin_outside_brain_fraction",
    "observed_component_count",
    "twin_component_count",
    "rt_start_day",
    "rt_started_by_t1",
    "treatment_reconstructable",
)


def _write_csv(
    path: Path,
    records: list[CohortPatientErrorRecord],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(_CSV_COLUMNS)

        for record in records:
            values: dict[str, object] = {
                **asdict(record),
                "qc_warning_count": len(record.qc_warning_codes),
                "qc_warning_codes": ";".join(record.qc_warning_codes),
            }
            writer.writerow(
                [values[column] for column in _CSV_COLUMNS]
            )


def _analysis_kind(
    evaluation: CohortEvaluationPayload,
) -> tuple[str, str]:
    evaluation_kind = evaluation["kind"]

    if evaluation_kind == "v2_cohort_evaluation":
        return "v2_cohort_error_analysis", "V2"

    if evaluation_kind == "v3_cohort_evaluation":
        if evaluation.get("model_version") != "V3":
            raise ValueError(
                "V3 cohort evaluation is missing model-version provenance"
            )
        return "v3_cohort_error_analysis", "V3"

    raise ValueError(
        f"Unsupported cohort evaluation kind: {evaluation_kind!r}"
    )


def _analysis_payload(
    *,
    evaluation: CohortEvaluationPayload,
    source_evaluation_sha256: str,
    analysis_config_sha256: str,
    config: CohortErrorAnalysisConfig,
    records: list[CohortPatientErrorRecord],
) -> dict[str, object]:
    summary = summarize_error_records(
        records,
        worst_patient_count=config.worst_patient_count,
        min_correlation_patients=config.min_correlation_patients,
    )
    kind, model_version = _analysis_kind(evaluation)

    payload: dict[str, object] = {
        "schema_version": COHORT_ERROR_ANALYSIS_SCHEMA_VERSION,
        "kind": kind,
        "sealed": True,
        "source_evaluation_sha256": source_evaluation_sha256,
        "source_freeze_manifest_sha256": (
            evaluation["source_freeze_manifest_sha256"]
        ),
        "analysis_config_sha256": analysis_config_sha256,
        "dataset": dict(evaluation["dataset"]),
        "repository": dict(evaluation["repository"]),
        "analysis_config": {
            "stable_volume_change_fraction": (
                config.stable_volume_change_fraction
            ),
            "worst_patient_count": config.worst_patient_count,
            "min_correlation_patients": (
                config.min_correlation_patients
            ),
        },
        "summary": asdict(summary),
        "patients": [asdict(record) for record in records],
    }

    if model_version == "V3":
        payload["model_version"] = model_version

    return payload


def analyze_sealed_cohort(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    analysis_config_path: Path,
    output_dir: Path,
) -> CohortErrorAnalysisResult:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            "Cohort error analysis destination already exists: "
            f"{destination}"
        )

    evaluation = load_sealed_cohort_evaluation(
        cohort_evaluation_root
    )
    config = load_cohort_error_analysis_config(
        analysis_config_path
    )
    spacing = target_spacing(evaluation.manifest)

    records = [
        _patient_record(
            metadata_root=metadata_root,
            patients_root=patients_root,
            cohort_freeze_root=cohort_freeze_root,
            cohort_evaluation_root=cohort_evaluation_root,
            patient=patient,
            evaluation_payload=evaluation.manifest,
            spacing=spacing,
            config=config,
        )
        for patient in sorted(
            evaluation.manifest["patients"],
            key=lambda item: item["patient_id"],
        )
    ]

    source_evaluation_sha256 = sha256_file(
        cohort_evaluation_root.resolve()
        / "cohort_evaluation.json"
    )
    payload = _analysis_payload(
        evaluation=evaluation.manifest,
        source_evaluation_sha256=source_evaluation_sha256,
        analysis_config_sha256=sha256_file(
            analysis_config_path.resolve()
        ),
        config=config,
        records=records,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )

    try:
        manifest_path = temporary / "cohort_analysis.json"
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (
            temporary / "cohort_analysis.sha256"
        ).write_text(
            sha256_file(manifest_path)
            + "  cohort_analysis.json\n",
            encoding="ascii",
        )
        _write_csv(
            temporary / "cohort_analysis.csv",
            records,
        )
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return load_sealed_cohort_analysis(destination)


def load_sealed_cohort_analysis(
    directory: Path,
) -> CohortErrorAnalysisResult:
    root = directory.resolve()
    manifest_path = root / "cohort_analysis.json"
    seal_path = root / "cohort_analysis.sha256"

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Cohort analysis manifest not found: "
            f"{manifest_path}"
        )
    if not seal_path.is_file():
        raise FileNotFoundError(
            "Cohort analysis seal not found: "
            f"{seal_path}"
        )

    tokens = seal_path.read_text(encoding="ascii").split()
    if not tokens:
        raise ValueError("Cohort analysis seal is empty")
    if sha256_file(manifest_path) != tokens[0]:
        raise ValueError("Cohort analysis checksum mismatch")

    raw: object = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    if not isinstance(raw, dict):
        raise ValueError(
            "Cohort analysis must contain a JSON object"
        )

    payload = cast(dict[str, object], raw)
    if (
        payload.get("schema_version")
        != COHORT_ERROR_ANALYSIS_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported cohort error analysis schema version"
        )

    kind = payload.get("kind")
    if kind == "v3_cohort_error_analysis":
        if payload.get("model_version") != "V3":
            raise ValueError(
                "V3 cohort error analysis is missing model-version provenance"
            )
    elif kind != "v2_cohort_error_analysis":
        raise ValueError(
            "Artifact is not a supported cohort error analysis"
        )

    if payload.get("sealed") is not True:
        raise ValueError("Cohort error analysis is not sealed")
    if not isinstance(payload.get("summary"), dict):
        raise ValueError(
            "Cohort error analysis summary is missing"
        )
    if not isinstance(payload.get("patients"), list):
        raise ValueError(
            "Cohort error analysis patient rows are missing"
        )

    return CohortErrorAnalysisResult(
        directory=root,
        manifest=payload,
    )
