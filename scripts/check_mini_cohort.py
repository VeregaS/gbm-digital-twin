from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.nifti import same_geometry
from gbm_twin.data.patient_loader import load_patient_timepoint
from gbm_twin.preprocessing.resampling import resample_volume


def main() -> None:
    metadata = CFBMetadata(
        Path(r"D:\Datasets\CFB-GBM\metadata")
    )

    patients_root = Path(
        r"D:\Datasets\CFB-GBM\patients"
    )

    for patient_id in [8, 18, 42]:
        patient = metadata.patient(patient_id)

        t0 = patient.get_timepoint("t0")
        t1 = patient.get_timepoint("t1")
        t2 = patient.get_timepoint("t2")

        studies = [
            load_patient_timepoint(
                patients_root,
                patient_id,
                timepoint,
            )
            for timepoint in [t0, t1, t2]
        ]

        gtvs = [
            resample_volume(
                study.gtv,
                (2.0, 2.0, 2.0),
                is_mask=True,
            )
            for study in studies
        ]

        print()
        print(f"Patient {patient_id}")
        print(
            f"dt01={patient.interval_days('t0', 't1')} days, "
            f"dt12={patient.interval_days('t1', 't2')} days"
        )

        print(
            "shapes:",
            [volume.shape for volume in gtvs],
        )

        print(
            "t0/t1 geometry:",
            same_geometry(gtvs[0], gtvs[1]),
        )

        print(
            "t1/t2 geometry:",
            same_geometry(gtvs[1], gtvs[2]),
        )


if __name__ == "__main__":
    main()