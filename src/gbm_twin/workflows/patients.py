from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.nifti import (
    NiftiVolume,
    same_geometry,
)
from gbm_twin.data.patient_loader import (
    load_patient_timepoint,
)
from gbm_twin.preprocessing.resampling import (
    resample_volume,
)

DEFAULT_TARGET_SPACING = (
    2.0,
    2.0,
    2.0,
)


@dataclass(frozen=True)
class PreparedPatientTimepoint:
    patient_id: int
    name: str
    days_from_baseline: float

    t1gd: NiftiVolume
    gtv: NiftiVolume
    brain_mask: NiftiVolume

    @property
    def spacing(
        self,
    ) -> tuple[
        float,
        float,
        float,
    ]:
        return self.gtv.spacing


def _validate_target_spacing(
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> None:
    if len(spacing) != 3:
        raise ValueError(
            "target_spacing must contain "
            "exactly three values"
        )

    if any(
        value <= 0
        for value in spacing
    ):
        raise ValueError(
            "target_spacing values must "
            "be positive"
        )


def _validate_geometry(
    *,
    patient_id: int,
    timepoint_name: str,
    t1gd: NiftiVolume,
    gtv: NiftiVolume,
    brain_mask: NiftiVolume,
) -> None:
    if not same_geometry(
        t1gd,
        gtv,
    ):
        raise ValueError(
            f"Patient {patient_id} "
            f"{timepoint_name}: "
            "T1Gd/GTV geometry mismatch"
        )

    if not same_geometry(
        gtv,
        brain_mask,
    ):
        raise ValueError(
            f"Patient {patient_id} "
            f"{timepoint_name}: "
            "GTV/brain geometry mismatch"
        )


def prepare_patient_timepoint(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ] = DEFAULT_TARGET_SPACING,
) -> PreparedPatientTimepoint:
    _validate_target_spacing(
        target_spacing
    )

    metadata = CFBMetadata(
        metadata_root
    )

    patient = metadata.patient(
        patient_id
    )

    timepoint = (
        patient.get_timepoint(
            timepoint_name
        )
    )
    
    days_from_baseline = (
        timepoint.days_from_baseline
    )

    if days_from_baseline is None:
        raise ValueError(
            f"Patient {patient_id} "
            f"{timepoint_name}: "
            "days_from_baseline is missing"
        )

    study = load_patient_timepoint(
        patients_root,
        patient_id,
        timepoint,
    )

    t1gd = resample_volume(
        study.t1gd,
        target_spacing,
        is_mask=False,
    )

    gtv = resample_volume(
        study.gtv,
        target_spacing,
        is_mask=True,
    )

    brain_mask = resample_volume(
        study.brain_mask,
        target_spacing,
        is_mask=True,
    )

    _validate_geometry(
        patient_id=patient_id,
        timepoint_name=(
            timepoint_name
        ),
        t1gd=t1gd,
        gtv=gtv,
        brain_mask=brain_mask,
    )

    return PreparedPatientTimepoint(
        patient_id=patient_id,
        name=timepoint_name,
        days_from_baseline=float(
            days_from_baseline
        ),
        t1gd=t1gd,
        gtv=gtv,
        brain_mask=brain_mask,
    )