from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gbm_twin.data.nifti import NiftiVolume, load_nifti, same_geometry
from gbm_twin.preprocessing.resampling import resample_volume_to_reference
from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    PreparedPatientTimepoint,
    prepare_patient_timepoint,
)


@dataclass(frozen=True)
class PreparedStage8Timepoint:
    base: PreparedPatientTimepoint
    flair: NiftiVolume | None
    diffusion: NiftiVolume | None


@dataclass(frozen=True)
class PreparedSpatialDose:
    volume: NiftiVolume
    source_path: Path


_MODALITY_FILENAMES: dict[str, tuple[str, ...]] = {
    "flair": (
        "{patient_id}_{timepoint}_flair.nii.gz",
        "{patient_id}_{timepoint}_t2flair.nii.gz",
        "{patient_id}_{timepoint}_t2_flair.nii.gz",
    ),
    "diffusion": (
        "{patient_id}_{timepoint}_adc.nii.gz",
        "{patient_id}_{timepoint}_dwi.nii.gz",
        "{patient_id}_{timepoint}_diffusion.nii.gz",
    ),
}


def _first_existing(
    directory: Path,
    candidates: tuple[str, ...],
) -> Path | None:
    matches = [
        directory / candidate
        for candidate in candidates
        if (directory / candidate).is_file()
    ]

    if len(matches) > 1:
        raise ValueError(
            "Multiple candidate files match one Stage 8 modality: "
            + ", ".join(str(path) for path in matches)
        )

    return matches[0] if matches else None


def _optional_modality_path(
    *,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    modality: str,
) -> Path | None:
    templates = _MODALITY_FILENAMES[modality]
    directory = patients_root / str(patient_id) / timepoint_name
    candidates = tuple(
        template.format(
            patient_id=patient_id,
            timepoint=timepoint_name,
        )
        for template in templates
    )
    return _first_existing(directory, candidates)


def _load_optional_on_reference(
    path: Path | None,
    reference: NiftiVolume,
) -> NiftiVolume | None:
    if path is None:
        return None

    volume = load_nifti(path)

    if same_geometry(volume, reference):
        return volume

    return resample_volume_to_reference(
        volume,
        reference,
        is_mask=False,
    )


def prepare_stage8_timepoint(
    *,
    metadata_root: Path,
    patients_root: Path,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[float, float, float] = DEFAULT_TARGET_SPACING,
) -> PreparedStage8Timepoint:
    base = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        target_spacing=target_spacing,
    )

    flair_path = _optional_modality_path(
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        modality="flair",
    )
    diffusion_path = _optional_modality_path(
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        modality="diffusion",
    )

    return PreparedStage8Timepoint(
        base=base,
        flair=_load_optional_on_reference(flair_path, base.t1gd),
        diffusion=_load_optional_on_reference(diffusion_path, base.t1gd),
    )


def discover_patient_rtdose_path(
    *,
    patients_root: Path,
    patient_id: int,
) -> Path | None:
    patient_root = patients_root / str(patient_id)

    if not patient_root.is_dir():
        return None

    patterns = (
        "**/*rtdose*.nii.gz",
        "**/*RTDOSE*.nii.gz",
        "**/*rt_dose*.nii.gz",
    )

    matches: set[Path] = set()

    for pattern in patterns:
        matches.update(
            path.resolve()
            for path in patient_root.glob(pattern)
            if path.is_file()
        )

    ordered = sorted(matches)

    if len(ordered) > 1:
        raise ValueError(
            f"Patient {patient_id}: multiple RTDOSE NIfTI files found: "
            + ", ".join(str(path) for path in ordered)
        )

    return ordered[0] if ordered else None


def prepare_spatial_rtdose(
    *,
    patients_root: Path,
    patient_id: int,
    reference: NiftiVolume,
) -> PreparedSpatialDose | None:
    path = discover_patient_rtdose_path(
        patients_root=patients_root,
        patient_id=patient_id,
    )

    if path is None:
        return None

    dose = load_nifti(path)

    if not same_geometry(dose, reference):
        dose = resample_volume_to_reference(
            dose,
            reference,
            is_mask=False,
        )

    return PreparedSpatialDose(
        volume=dose,
        source_path=path,
    )
