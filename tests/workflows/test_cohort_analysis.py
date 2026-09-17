from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.cohort_analysis as analysis_module
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.workflows.cohort_analysis import (
    analyze_sealed_cohort,
    load_sealed_cohort_analysis,
)
from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationPayload,
    CohortEvaluationResult,
)
from gbm_twin.workflows.patient_catalog import (
    PatientCatalogSummary,
    PatientCatalogTimepoint,
    PatientTreatmentSummary,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)
from gbm_twin.workflows.twin_qc import (
    TwinMaskQC,
    TwinPatientQC,
)


def _evaluation_payload() -> CohortEvaluationPayload:
    return {
        "schema_version": 1,
        "kind": "v2_cohort_evaluation",
        "sealed": True,
        "source_freeze_manifest_sha256": "a" * 64,
        "dataset": {
            "name": "CFB-GBM",
            "version": 4,
            "doi": "10.7937/v9pn-2f72",
        },
        "repository": {
            "commit_sha": "0123456789abcdef",
            "dirty": False,
        },
        "target_spacing": [
            2.0,
            2.0,
            2.0,
        ],
        "source_artifacts": [
            {
                "patient_id": 42,
                "artifact_dir": "patients/patient-42/frozen-v2",
                "manifest_sha256": "b" * 64,
            }
        ],
        "patients": [
            {
                "patient_id": 42,
                "target_timepoint": "t2",
                "target_day": 150.0,
                "twin": {
                    "dice": 0.80,
                    "relative_volume_error": 0.10,
                    "hd95_mm": 4.0,
                    "centroid_distance_mm": 2.0,
                },
                "persistence": {
                    "dice": 0.70,
                    "relative_volume_error": 0.20,
                    "hd95_mm": 6.0,
                    "centroid_distance_mm": 3.0,
                },
                "volume_baseline": {
                    "dice": 0.75,
                    "relative_volume_error": 0.15,
                    "hd95_mm": 5.0,
                    "centroid_distance_mm": 2.5,
                },
            }
        ],
    }


def _volume(
    path: str,
    mask_voxels: int,
) -> NiftiVolume:
    data = np.zeros(
        (4, 4, 4),
        dtype=np.float32,
    )

    data.reshape(-1)[
        :mask_voxels
    ] = 1.0

    return NiftiVolume(
        path=Path(path),
        data=data,
        affine=np.eye(
            4,
            dtype=np.float64,
        ),
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )


def _prepared(
    name: str,
) -> PreparedPatientTimepoint:
    voxels_by_name = {
        "t0": 10,
        "t1": 12,
        "t2": 18,
    }

    gtv = _volume(
        f"{name}_gtv.nii.gz",
        voxels_by_name[name],
    )

    brain = _volume(
        f"{name}_brain.nii.gz",
        64,
    )

    image = _volume(
        f"{name}_t1gd.nii.gz",
        32,
    )

    day_by_name = {
        "t0": 0.0,
        "t1": 60.0,
        "t2": 150.0,
    }

    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=(
            day_by_name[name]
        ),
        t1gd=image,
        gtv=gtv,
        brain_mask=brain,
    )


def _catalog() -> PatientCatalogSummary:
    return PatientCatalogSummary(
        patient_id=42,
        timepoints=(
            PatientCatalogTimepoint(
                name="t0",
                days_from_baseline=0.0,
                gtv_available=True,
                gtv_type="GTV",
                rtdose_available=False,
            ),
            PatientCatalogTimepoint(
                name="t1",
                days_from_baseline=60.0,
                gtv_available=True,
                gtv_type="GTV",
                rtdose_available=True,
            ),
            PatientCatalogTimepoint(
                name="t2",
                days_from_baseline=150.0,
                gtv_available=True,
                gtv_type="GTV",
                rtdose_available=True,
            ),
        ),
        dt01_days=60.0,
        dt12_days=90.0,
        treatment=PatientTreatmentSummary(
            has_record=True,
            rt_start_day=7.0,
            rt_start_phase="during_calibration",
            rt_started_by_t1=True,
            rt_started_by_t2=True,
            dose_gy=60.0,
            fractions=30,
            reconstructable=True,
        ),
    )


def _artifact(
    tmp_path: Path,
) -> FrozenV2PredictionArtifact:
    mask = np.zeros(
        (4, 4, 4),
        dtype=np.uint8,
    )

    return FrozenV2PredictionArtifact(
        directory=tmp_path / "artifact",
        manifest={
            "patient_id": 42,
            "parameters": {
                "diffusion": 0.015,
                "proliferation": 0.035,
            },
            "calibration": {
                "best": {
                    "dice": 0.90,
                    "volume_error": 0.08,
                    "loss": 0.12,
                },
                "diagnostics": {
                    "identifiable": True,
                    "diffusion_at_boundary": False,
                    "proliferation_at_boundary": False,
                },
            },
        },
        prediction_field=(
            mask.astype(np.float32)
        ),
        prediction_mask=mask,
        persistence_mask=mask,
        volume_baseline_mask=mask,
    )


def _mask_qc(
    name: str,
) -> TwinMaskQC:
    return TwinMaskQC(
        name=name,
        voxel_count=10,
        volume_cm3=0.08,
        component_count=1,
        largest_component_fraction=1.0,
        outside_brain_voxels=0,
        outside_brain_fraction=0.0,
        centroid_inside_brain=True,
    )


def _qc() -> TwinPatientQC:
    return TwinPatientQC(
        patient_id=42,
        observed=_mask_qc("observed"),
        twin=_mask_qc("twin"),
        persistence=_mask_qc("persistence"),
        volume_baseline=_mask_qc("volume_baseline"),
        warnings=(),
    )


def test_analyze_sealed_cohort_writes_reproducible_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evaluation_payload = _evaluation_payload()

    evaluation_root = (
        tmp_path
        / "evaluation"
    )
    evaluation_root.mkdir()

    (
        evaluation_root
        / "cohort_evaluation.json"
    ).write_text(
        "{}\n",
        encoding="utf-8",
    )

    config_path = (
        tmp_path
        / "analysis.yaml"
    )
    config_path.write_text(
        "schema_version: 1\n"
        "stable_volume_change_fraction: 0.10\n"
        "worst_patient_count: 5\n"
        "min_correlation_patients: 3\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        analysis_module,
        "load_sealed_cohort_evaluation",
        lambda directory: CohortEvaluationResult(
            directory=directory,
            manifest=evaluation_payload,
        ),
    )

    monkeypatch.setattr(
        analysis_module,
        "get_patient_catalog_summary",
        lambda **kwargs: _catalog(),
    )

    monkeypatch.setattr(
        analysis_module,
        "prepare_patient_timepoint",
        lambda **kwargs: _prepared(
            str(kwargs["timepoint_name"])
        ),
    )

    artifact = _artifact(
        tmp_path
    )

    monkeypatch.setattr(
        analysis_module,
        "load_frozen_patient_artifact",
        lambda **kwargs: artifact,
    )

    monkeypatch.setattr(
        analysis_module,
        "get_twin_patient_qc",
        lambda **kwargs: _qc(),
    )

    output_dir = (
        tmp_path
        / "analysis"
    )

    result = analyze_sealed_cohort(
        metadata_root=tmp_path / "metadata",
        patients_root=tmp_path / "patients",
        cohort_freeze_root=tmp_path / "freeze",
        cohort_evaluation_root=(
            evaluation_root
        ),
        analysis_config_path=(
            config_path
        ),
        output_dir=output_dir,
    )

    assert result.directory == output_dir.resolve()

    assert (
        output_dir
        / "cohort_analysis.json"
    ).is_file()
    assert (
        output_dir
        / "cohort_analysis.sha256"
    ).is_file()
    assert (
        output_dir
        / "cohort_analysis.csv"
    ).is_file()

    patients = result.manifest[
        "patients"
    ]

    assert isinstance(
        patients,
        list,
    )

    row = patients[0]

    assert isinstance(
        row,
        dict,
    )

    assert row["patient_id"] == 42
    assert row["forecast_horizon_days"] == pytest.approx(90.0)
    assert row["volume_change_t1_t2"] == pytest.approx(0.5)
    assert row["twin_minus_persistence_dice"] == pytest.approx(0.1)
    assert row["diffusion"] == pytest.approx(0.015)
    assert row["calibration_identifiable"] is True

    loaded = load_sealed_cohort_analysis(
        output_dir
    )

    assert loaded.manifest == result.manifest


def test_load_sealed_cohort_analysis_rejects_tampering(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evaluation_payload = _evaluation_payload()
    evaluation_root = tmp_path / "evaluation"
    evaluation_root.mkdir()

    (
        evaluation_root
        / "cohort_evaluation.json"
    ).write_text(
        "{}\n",
        encoding="utf-8",
    )

    config_path = tmp_path / "analysis.yaml"
    config_path.write_text(
        "schema_version: 1\n"
        "stable_volume_change_fraction: 0.10\n"
        "worst_patient_count: 5\n"
        "min_correlation_patients: 3\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        analysis_module,
        "load_sealed_cohort_evaluation",
        lambda directory: CohortEvaluationResult(
            directory=directory,
            manifest=evaluation_payload,
        ),
    )
    monkeypatch.setattr(
        analysis_module,
        "get_patient_catalog_summary",
        lambda **kwargs: _catalog(),
    )
    monkeypatch.setattr(
        analysis_module,
        "prepare_patient_timepoint",
        lambda **kwargs: _prepared(
            str(kwargs["timepoint_name"])
        ),
    )
    monkeypatch.setattr(
        analysis_module,
        "load_frozen_patient_artifact",
        lambda **kwargs: _artifact(tmp_path),
    )
    monkeypatch.setattr(
        analysis_module,
        "get_twin_patient_qc",
        lambda **kwargs: _qc(),
    )

    output_dir = tmp_path / "analysis"

    analyze_sealed_cohort(
        metadata_root=tmp_path / "metadata",
        patients_root=tmp_path / "patients",
        cohort_freeze_root=tmp_path / "freeze",
        cohort_evaluation_root=evaluation_root,
        analysis_config_path=config_path,
        output_dir=output_dir,
    )

    manifest_path = (
        output_dir
        / "cohort_analysis.json"
    )

    manifest_path.write_text(
        manifest_path.read_text(
            encoding="utf-8"
        )
        + " ",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="checksum mismatch",
    ):
        load_sealed_cohort_analysis(
            output_dir
        )
