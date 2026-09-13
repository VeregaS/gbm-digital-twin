from pathlib import Path

import pandas as pd

from gbm_twin.data.models import Patient, Timepoint


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
    
    def patient_timeline(self, patient_id: int) -> list[Timepoint]:
        rows = self.mri[self.mri["id_patient"] == patient_id].copy()

        if rows.empty:
            raise KeyError(f"Unknown patient: {patient_id}")

        rows = rows.sort_values("time_diff_t0 (weeks)")

        timeline: list[Timepoint] = []

        for _, row in rows.iterrows():
            weeks_from_baseline = float(row["time_diff_t0 (weeks)"])

            timeline.append(
                Timepoint(
                    name=str(row["temporality"]),
                    days_from_baseline=round(weeks_from_baseline * 7),
                )
            )

        return timeline
    
    def patient(self, patient_id: int) -> Patient:
        patient = Patient(patient_id=str(patient_id))

        for timepoint in self.patient_timeline(patient_id):
            patient.add_timepoint(timepoint)

        return patient
    
    def has_modality(
        self,
        patient_id: int,
        timepoint: str,
        modality: str,
    ) -> bool:
        rows = self.mri[
            (self.mri["id_patient"] == patient_id)
            & (self.mri["temporality"] == timepoint)
        ]

        if rows.empty:
            return False

        if modality not in self.mri.columns:
            raise KeyError(f"Unknown MRI modality: {modality}")

        return bool(rows.iloc[0][modality] == 1)


    def imaging_cohort(
        self,
        required_modalities: set[str] | None = None,
    ) -> list[int]:
        if required_modalities is None:
            required_modalities = {"t1gd"}

        required_timepoints = ("t0", "t1", "t2")

        eligible: list[int] = []

        for patient_id in self.prediction_cohort():
            if all(
                self.has_modality(patient_id, timepoint, modality)
                for timepoint in required_timepoints
                for modality in required_modalities
            ):
                eligible.append(patient_id)

        return eligible