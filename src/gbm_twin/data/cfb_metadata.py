from pathlib import Path

import pandas as pd


class CFBMetadata:
    def __init__(self, metadata_dir: Path) -> None:
        self.metadata_dir = metadata_dir

        self.mri = self._read_single("CFB-GBM_mri_availability_*.tsv")
        self.rano = self._read_single("CFB-GBM_rano_criteria_*.tsv")

    def _read_single(self, pattern: str) -> pd.DataFrame:
        files = list(self.metadata_dir.glob(pattern))

        if len(files) != 1:
            raise RuntimeError(
                f"Expected exactly one file matching {pattern!r}, found {len(files)}"
            )

        return pd.read_csv(files[0], sep="\t")

    def patient_ids(self) -> list[int]:
        return sorted(self.mri["id_patient"].unique().tolist())

    def timepoints(self, patient_id: int) -> set[str]:
        rows = self.mri[self.mri["id_patient"] == patient_id]
        return set(rows["temporality"].tolist())

    def longitudinal_patients(
        self,
        required_timepoints: set[str] | None = None,
    ) -> list[int]:
        if required_timepoints is None:
            required_timepoints = {"t0", "t1", "t2"}

        return [
            patient_id
            for patient_id in self.patient_ids()
            if required_timepoints.issubset(self.timepoints(patient_id))
        ]
        
    def prediction_cohort(self) -> list[int]:
        required_columns = [
            "size_t0 (cm3)",
            "size_t1 (cm3)",
            "size_t2 (cm3)",
        ]

        complete_rano = self.rano.dropna(subset=required_columns)

        rano_patient_ids = set(complete_rano["id_patient"].tolist())
        longitudinal_patient_ids = set(self.longitudinal_patients())

        return sorted(longitudinal_patient_ids & rano_patient_ids)