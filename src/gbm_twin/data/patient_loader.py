from pathlib import Path

from gbm_twin.data.models import PatientTimepointStudy, Timepoint
from gbm_twin.data.nifti import load_nifti, same_geometry


def load_patient_timepoint(
    patients_root: Path,
    patient_id: int | str,
    timepoint: Timepoint,
) -> PatientTimepointStudy:
    patient_id_str = str(patient_id)
    timepoint_dir = patients_root / patient_id_str / timepoint.name

    t1gd_path = timepoint_dir / f"{patient_id_str}_{timepoint.name}_t1gd.nii.gz"
    gtv_path = timepoint_dir / f"{patient_id_str}_{timepoint.name}_gtv.nii.gz"
    brain_mask_path = timepoint_dir / f"{patient_id_str}_{timepoint.name}_brain_mask.nii.gz"

    t1gd = load_nifti(t1gd_path)
    gtv = load_nifti(gtv_path)
    brain_mask = load_nifti(brain_mask_path)

    if not same_geometry(t1gd, gtv):
        raise ValueError(
            f"Geometry mismatch between T1Gd and GTV for "
            f"patient {patient_id_str}, timepoint {timepoint.name}"
        )

    if not same_geometry(t1gd, brain_mask):
        raise ValueError(
            f"Geometry mismatch between T1Gd and brain mask for "
            f"patient {patient_id_str}, timepoint {timepoint.name}"
        )

    return PatientTimepointStudy(
        patient_id=patient_id_str,
        timepoint=timepoint,
        t1gd=t1gd,
        gtv=gtv,
        brain_mask=brain_mask,
    )