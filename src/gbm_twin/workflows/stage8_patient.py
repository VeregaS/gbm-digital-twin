from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.data.nifti import same_geometry
from gbm_twin.models.observation import (
    MRIDetectionObservationParameters,
    latent_density_from_mri_detection,
)
from gbm_twin.models.rt_schedule import (
    ReconstructedRadiotherapySchedule,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.treatment_memory import (
    TreatmentMemoryState,
    initial_treatment_memory_state,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
    prepare_patient_timepoint,
)
from gbm_twin.workflows.stage8_inputs import prepare_spatial_rtdose


@dataclass(frozen=True)
class Stage8ForecastInputs:
    """Pre-t2 patient inputs reusable across Stage 8 model candidates."""

    patient_id: int
    start: PreparedPatientTimepoint
    observed: PreparedPatientTimepoint
    schedule: ReconstructedRadiotherapySchedule
    domain_mask: np.ndarray
    initial_state: TreatmentMemoryState
    cumulative_rtdose: np.ndarray | None
    rtdose_source_path: Path | None


@dataclass(frozen=True)
class Stage8EvaluationTarget:
    """Outcome image loaded only by a workflow allowed to reveal t2."""

    patient_id: int
    target: PreparedPatientTimepoint


def _require_registered(
    first: PreparedPatientTimepoint,
    second: PreparedPatientTimepoint,
    *,
    label: str,
) -> None:
    if first.patient_id != second.patient_id:
        raise ValueError(f"{label}: patient IDs do not match")

    if not same_geometry(first.gtv, second.gtv):
        raise ValueError(f"{label}: GTV geometry mismatch")

    if not same_geometry(first.brain_mask, second.brain_mask):
        raise ValueError(f"{label}: brain-mask geometry mismatch")


def _schedule(
    treatment: CFBTreatmentMetadata,
    patient_id: int,
) -> ReconstructedRadiotherapySchedule:
    record = treatment.treatment(patient_id)

    if (
        record is None
        or record.radiotherapy_start_day is None
        or record.dose_gy is None
        or record.fractions_number is None
    ):
        raise ValueError(
            f"Patient {patient_id}: complete RT schedule is required"
        )

    return reconstruct_weekday_like_schedule(
        start_day=record.radiotherapy_start_day,
        total_dose_gy=record.dose_gy,
        fractions_number=record.fractions_number,
    )


def prepare_stage8_forecast_inputs(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    target_spacing: tuple[float, float, float],
    treatment: CFBTreatmentMetadata,
    observation_parameters: MRIDetectionObservationParameters,
    load_spatial_rtdose: bool = True,
) -> Stage8ForecastInputs:
    """Load t0/t1 and reusable treatment inputs without opening t2."""

    start = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t0",
        target_spacing=target_spacing,
    )
    observed = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t1",
        target_spacing=target_spacing,
    )
    _require_registered(start, observed, label="Stage 8 t0/t1")

    domain = np.asarray(
        (start.brain_mask.data > 0.5)
        | (observed.brain_mask.data > 0.5)
        | (start.gtv.data > 0.5)
        | (observed.gtv.data > 0.5),
        dtype=bool,
    )
    initial_density = latent_density_from_mri_detection(
        start.gtv.data > 0.5,
        domain,
        spacing=start.spacing,
        parameters=observation_parameters,
    )
    initial_state = initial_treatment_memory_state(
        initial_density,
        domain_mask=domain,
    )

    cumulative_rtdose: np.ndarray | None = None
    rtdose_source_path: Path | None = None

    if load_spatial_rtdose:
        prepared_dose = prepare_spatial_rtdose(
            patients_root=patients_root,
            patient_id=patient_id,
            reference=start.t1gd,
        )

        if prepared_dose is not None:
            cumulative_rtdose = np.asarray(
                prepared_dose.volume.data,
                dtype=np.float32,
            )
            rtdose_source_path = prepared_dose.source_path

    return Stage8ForecastInputs(
        patient_id=patient_id,
        start=start,
        observed=observed,
        schedule=_schedule(treatment, patient_id),
        domain_mask=domain,
        initial_state=initial_state,
        cumulative_rtdose=cumulative_rtdose,
        rtdose_source_path=rtdose_source_path,
    )


def prepare_stage8_evaluation_target(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    target_spacing: tuple[float, float, float],
    reference: PreparedPatientTimepoint,
) -> Stage8EvaluationTarget:
    """Explicit t2 reveal step separated from pre-forecast input loading."""

    target = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t2",
        target_spacing=target_spacing,
    )
    _require_registered(reference, target, label="Stage 8 t1/t2")

    return Stage8EvaluationTarget(
        patient_id=patient_id,
        target=target,
    )
