from __future__ import annotations

from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.data.dataset_manifest import CFBDatasetManifest
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.rt_schedule import (
    build_pirt_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.treatment import PIRTFractionatedRadiotherapy
from gbm_twin.workflows.calibration import (
    V2_ALPHA_BETA_RATIO_GY,
    V2_EFFECTIVE_ALPHA_PER_GY,
    V2CalibrationConfig,
)
from gbm_twin.workflows.contracts import PredictionTarget
from gbm_twin.workflows.eligibility import (
    PatientEligibility,
    assess_patient_eligibility,
)
from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    PreparedPatientTimepoint,
    prepare_patient_timepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenV2PredictionArtifact,
    freeze_v2_prediction,
)
from gbm_twin.workflows.provenance import (
    build_prediction_provenance,
)


class PatientNotEligibleError(RuntimeError):
    def __init__(
        self,
        eligibility: PatientEligibility,
    ) -> None:
        self.eligibility = eligibility

        reasons = ", ".join(
            eligibility.reason_codes
        )

        super().__init__(
            f"Patient {eligibility.patient_id} "
            f"is not eligible: {reasons}"
        )


class PatientTwinService:
    def __init__(
        self,
        *,
        metadata_root: Path,
        patients_root: Path,
        dataset_manifest: CFBDatasetManifest,
        calibration_config: V2CalibrationConfig,
        git_commit_sha: str,
        git_dirty: bool,
        target_spacing: tuple[
            float,
            float,
            float,
        ] = DEFAULT_TARGET_SPACING,
    ) -> None:
        self._metadata_root = metadata_root
        self._patients_root = patients_root
        self._dataset_manifest = dataset_manifest
        self._calibration_config = calibration_config
        self._git_commit_sha = git_commit_sha
        self._git_dirty = git_dirty
        self._target_spacing = target_spacing

        self._metadata = CFBMetadata(
            metadata_root
        )

        self._treatment_metadata = (
            CFBTreatmentMetadata(
                metadata_root
            )
        )

    def assess_eligibility(
        self,
        patient_id: int,
    ) -> PatientEligibility:
        return assess_patient_eligibility(
            metadata=self._metadata,
            manifest=self._dataset_manifest,
            patients_root=self._patients_root,
            patient_id=patient_id,
            treatment_metadata=(
                self._treatment_metadata
            ),
            require_treatment_schedule=True,
        )

    def _prediction_target(
        self,
        patient_id: int,
    ) -> PredictionTarget:
        patient = self._metadata.patient(
            patient_id
        )

        target_timepoint = (
            patient.get_timepoint(
                "t2"
            )
        )

        target_day = (
            target_timepoint
            .days_from_baseline
        )

        if target_day is None:
            raise ValueError(
                f"Patient {patient_id} t2: "
                "days_from_baseline is missing"
            )

        return PredictionTarget(
            timepoint_name="t2",
            target_day=float(
                target_day
            ),
        )

    def _prepare_timepoint(
        self,
        *,
        patient_id: int,
        timepoint_name: str,
    ) -> PreparedPatientTimepoint:
        return prepare_patient_timepoint(
            metadata_root=(
                self._metadata_root
            ),
            patients_root=(
                self._patients_root
            ),
            patient_id=patient_id,
            timepoint_name=(
                timepoint_name
            ),
            target_spacing=(
                self._target_spacing
            ),
        )

    def _treatment(
        self,
        patient_id: int,
    ) -> PIRTFractionatedRadiotherapy:
        record = (
            self._treatment_metadata
            .treatment(
                patient_id
            )
        )

        if record is None:
            raise RuntimeError(
                f"Patient {patient_id}: "
                "treatment record became "
                "unavailable after eligibility"
            )

        start_day = (
            record.radiotherapy_start_day
        )

        total_dose_gy = (
            record.dose_gy
        )

        fractions_number = (
            record.fractions_number
        )

        if (
            start_day is None
            or total_dose_gy is None
            or fractions_number is None
        ):
            raise RuntimeError(
                f"Patient {patient_id}: "
                "treatment schedule became "
                "incomplete after eligibility"
            )

        schedule = (
            reconstruct_weekday_like_schedule(
                start_day=start_day,
                total_dose_gy=(
                    total_dose_gy
                ),
                fractions_number=(
                    fractions_number
                ),
            )
        )

        radiobiology = (
            RadiobiologyParameters(
                alpha_per_gy=(
                    V2_EFFECTIVE_ALPHA_PER_GY
                ),
                alpha_beta_ratio_gy=(
                    V2_ALPHA_BETA_RATIO_GY
                ),
            )
        )

        return build_pirt_radiotherapy(
            schedule,
            radiobiology,
        )

    def freeze_patient(
        self,
        *,
        patient_id: int,
        cache_dir: Path,
        output_dir: Path,
        workers: int = 1,
    ) -> FrozenV2PredictionArtifact:
        eligibility = (
            self.assess_eligibility(
                patient_id
            )
        )

        if not eligibility.eligible:
            raise PatientNotEligibleError(
                eligibility
            )

        target = self._prediction_target(
            patient_id
        )

        start = self._prepare_timepoint(
            patient_id=patient_id,
            timepoint_name="t0",
        )

        observed = (
            self._prepare_timepoint(
                patient_id=patient_id,
                timepoint_name="t1",
            )
        )

        treatment = self._treatment(
            patient_id
        )

        provenance = (
            build_prediction_provenance(
                dataset=(
                    self._dataset_manifest
                ),
                config=(
                    self._calibration_config
                ),
                start=start,
                observed=observed,
                git_commit_sha=(
                    self._git_commit_sha
                ),
                git_dirty=(
                    self._git_dirty
                ),
            )
        )

        return freeze_v2_prediction(
            start=start,
            observed=observed,
            target=target,
            provenance=provenance,
            treatment=treatment,
            config=(
                self._calibration_config
            ),
            cache_dir=cache_dir,
            output_dir=output_dir,
            workers=workers,
        )