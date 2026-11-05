from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.patient_twin as patient_twin_module
from gbm_twin.data.cfb_treatment import TreatmentRecord
from gbm_twin.data.dataset_manifest import CFBDatasetManifest
from gbm_twin.data.models import Patient, Timepoint
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.models.treatment import (
    PIRTFractionatedRadiotherapy,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
)
from gbm_twin.workflows.contracts import PredictionTarget
from gbm_twin.workflows.eligibility import (
    EligibilityIssue,
    EligibilityReason,
    PatientEligibility,
)
from gbm_twin.workflows.patient_twin import (
    PatientNotEligibleError,
    PatientTwinService,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
)
from gbm_twin.workflows.provenance import (
    InputFileProvenance,
    PredictionProvenance,
)


@dataclass
class CapturedCalls:
    prepared_timepoints: list[str]
    freeze_target_day: float | None = None
    freeze_treatment: (
        PIRTFractionatedRadiotherapy
        | None
    ) = None


class FakeMetadata:
    def __init__(
        self,
        metadata_root: Path,
    ) -> None:
        self.metadata_root = metadata_root

    def patient(
        self,
        patient_id: int,
    ) -> Patient:
        patient = Patient(
            patient_id=str(
                patient_id
            )
        )

        patient.add_timepoint(
            Timepoint(
                name="t0",
                days_from_baseline=0,
            )
        )

        patient.add_timepoint(
            Timepoint(
                name="t1",
                days_from_baseline=60,
            )
        )

        patient.add_timepoint(
            Timepoint(
                name="t2",
                days_from_baseline=120,
            )
        )

        return patient


class FakeTreatmentMetadata:
    def __init__(
        self,
        metadata_root: Path,
    ) -> None:
        self.metadata_root = metadata_root

    def treatment(
        self,
        patient_id: int,
    ) -> TreatmentRecord | None:
        return TreatmentRecord(
            patient_id=patient_id,
            delay_t0_to_radiotherapy_weeks=2.0,
            dose_gy=60.0,
            fractions_number=30,
        )


def make_manifest() -> CFBDatasetManifest:
    return CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source="The Cancer Imaging Archive",
        license="CC BY 4.0",
        expected_subjects=264,
        metadata_patterns=(
            "CFB-GBM_mri_availability_*.tsv",
            "CFB-GBM_rano_criteria_*.tsv",
            (
                "CFB-GBM_treatment_"
                "imaging_availability_*.tsv"
            ),
        ),
        required_timepoints=(
            "t0",
            "t1",
            "t2",
        ),
        required_modalities=(
            "t1gd",
        ),
        required_patient_files=(
            (
                "{patient_id}_"
                "{timepoint}_t1gd.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_gtv.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_brain_mask.nii.gz"
            ),
        ),
    )


def make_config() -> V2CalibrationConfig:
    return V2CalibrationConfig(
        diffusion_values=(
            0.01,
            0.03,
            0.05,
        ),
        proliferation_values=(
            0.005,
            0.015,
            0.025,
        ),
    )


def make_volume(
    name: str,
) -> NiftiVolume:
    return NiftiVolume(
        path=Path(name),
        data=np.zeros(
            (3, 3, 3),
            dtype=np.float32,
        ),
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


def make_timepoint(
    name: str,
    day: float,
) -> PreparedPatientTimepoint:
    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=make_volume(
            f"{name}_t1gd.nii.gz"
        ),
        gtv=make_volume(
            f"{name}_gtv.nii.gz"
        ),
        brain_mask=make_volume(
            f"{name}_brain_mask.nii.gz"
        ),
    )


def make_provenance() -> PredictionProvenance:
    return PredictionProvenance(
        dataset_name="CFB-GBM",
        dataset_version=4,
        dataset_doi=(
            "10.7937/v9pn-2f72"
        ),
        git_commit_sha=(
            "0123456789abcdef"
            "0123456789abcdef"
            "01234567"
        ),
        git_dirty=False,
        config_sha256="a" * 64,
        inputs=(
            InputFileProvenance(
                logical_name="t0_gtv",
                filename="t0_gtv.nii.gz",
                sha256="b" * 64,
            ),
        ),
    )


def make_artifact(
    output_dir: Path,
) -> FrozenV2PredictionArtifact:
    field = np.zeros(
        (3, 3, 3),
        dtype=np.float32,
    )

    mask = np.zeros(
        (3, 3, 3),
        dtype=bool,
    )

    return FrozenV2PredictionArtifact(
        directory=output_dir,
        manifest={
            "sealed": True,
        },
        prediction_field=field,
        prediction_mask=mask,
        persistence_mask=mask.copy(),
        volume_baseline_mask=mask.copy(),
    )


def make_service(
    tmp_path: Path,
) -> PatientTwinService:
    return PatientTwinService(
        metadata_root=(
            tmp_path
            / "metadata"
        ),
        patients_root=(
            tmp_path
            / "patients"
        ),
        dataset_manifest=make_manifest(),
        calibration_config=make_config(),
        git_commit_sha=(
            "0123456789abcdef"
            "0123456789abcdef"
            "01234567"
        ),
        git_dirty=False,
    )


def test_freeze_patient_never_prepares_t2(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured = CapturedCalls(
        prepared_timepoints=[]
    )

    monkeypatch.setattr(
        patient_twin_module,
        "CFBMetadata",
        FakeMetadata,
    )

    monkeypatch.setattr(
        patient_twin_module,
        "CFBTreatmentMetadata",
        FakeTreatmentMetadata,
    )

    monkeypatch.setattr(
        patient_twin_module,
        "assess_patient_eligibility",
        lambda **kwargs: PatientEligibility(
            patient_id=42,
            issues=(),
        ),
    )

    def fake_prepare_patient_timepoint(
        *,
        metadata_root: Path,
        patients_root: Path,
        patient_id: int,
        timepoint_name: str,
        target_spacing: tuple[
            float,
            float,
            float,
        ],
    ) -> PreparedPatientTimepoint:
        captured.prepared_timepoints.append(
            timepoint_name
        )

        day = (
            0.0
            if timepoint_name == "t0"
            else 60.0
        )

        return make_timepoint(
            timepoint_name,
            day,
        )

    monkeypatch.setattr(
        patient_twin_module,
        "prepare_patient_timepoint",
        fake_prepare_patient_timepoint,
    )

    monkeypatch.setattr(
        patient_twin_module,
        "build_prediction_provenance",
        lambda **kwargs: make_provenance(),
    )

    def fake_freeze_v2_prediction(
        *,
        start: PreparedPatientTimepoint,
        observed: PreparedPatientTimepoint,
        target: PredictionTarget,
        provenance: PredictionProvenance,
        treatment: (
            PIRTFractionatedRadiotherapy
            | None
        ),
        config: V2CalibrationConfig,
        cache_dir: Path,
        output_dir: Path,
        workers: int = 1,
    ) -> FrozenV2PredictionArtifact:
        assert start.name == "t0"
        assert observed.name == "t1"

        captured.freeze_target_day = (
            target.target_day
        )

        captured.freeze_treatment = (
            treatment
        )

        return make_artifact(
            output_dir
        )

    monkeypatch.setattr(
        patient_twin_module,
        "freeze_v2_prediction",
        fake_freeze_v2_prediction,
    )

    service = make_service(
        tmp_path
    )

    result = service.freeze_patient(
        patient_id=42,
        cache_dir=(
            tmp_path
            / "cache"
        ),
        output_dir=(
            tmp_path
            / "artifact"
        ),
        workers=2,
    )

    assert result.manifest["sealed"] is True

    assert (
        captured.prepared_timepoints
        == [
            "t0",
            "t1",
        ]
    )

    assert (
        captured.freeze_target_day
        == 120.0
    )

    assert (
        captured.freeze_treatment
        is not None
    )


def test_ineligible_patient_is_rejected_before_preparation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        patient_twin_module,
        "CFBMetadata",
        FakeMetadata,
    )

    monkeypatch.setattr(
        patient_twin_module,
        "CFBTreatmentMetadata",
        FakeTreatmentMetadata,
    )

    eligibility = PatientEligibility(
        patient_id=42,
        issues=(
            EligibilityIssue(
                reason=(
                    EligibilityReason
                    .TREATMENT_SCHEDULE_UNAVAILABLE
                ),
                detail=(
                    "RT schedule unavailable"
                ),
            ),
        ),
    )

    monkeypatch.setattr(
        patient_twin_module,
        "assess_patient_eligibility",
        lambda **kwargs: eligibility,
    )

    def fail_prepare(
        **kwargs: object,
    ) -> PreparedPatientTimepoint:
        pytest.fail(
            "Patient preparation must not "
            "run for an ineligible patient"
        )

    monkeypatch.setattr(
        patient_twin_module,
        "prepare_patient_timepoint",
        fail_prepare,
    )

    service = make_service(
        tmp_path
    )

    with pytest.raises(
        PatientNotEligibleError,
        match="treatment_schedule_unavailable",
    ) as exc_info:
        service.freeze_patient(
            patient_id=42,
            cache_dir=(
                tmp_path
                / "cache"
            ),
            output_dir=(
                tmp_path
                / "artifact"
            ),
        )

    assert (
        exc_info.value.eligibility
        == eligibility
    )