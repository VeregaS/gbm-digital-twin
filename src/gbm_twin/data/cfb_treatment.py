from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

_TREATMENT_COLUMNS = {
    "id_patient",
    "delay_t0_to_radiotherapy (weeks)",
    "dose (Gy)",
    "fractions_number",
}

_IMAGING_COLUMNS = {
    "id_patient",
    "temporality",
    "gtv",
    "gtv_type",
    "rtdose",
    "treatment_machine",
    "tps",
}


@dataclass(frozen=True)
class TreatmentRecord:
    patient_id: int
    delay_t0_to_radiotherapy_weeks: float | None
    dose_gy: float | None
    fractions_number: int | None

    @property
    def radiotherapy_start_day(self) -> float | None:
        if self.delay_t0_to_radiotherapy_weeks is None:
            return None

        return self.delay_t0_to_radiotherapy_weeks * 7.0


@dataclass(frozen=True)
class TreatmentImagingRecord:
    patient_id: int
    temporality: str
    gtv_available: bool
    gtv_type: str | None
    rtdose_available: bool
    treatment_machine: str | None
    tps: str | None


@dataclass(frozen=True)
class PatientTreatmentContext:
    patient_id: int

    has_treatment_record: bool

    rt_start_day: float | None
    rt_start_phase: str

    rt_started_by_t1: bool | None
    rt_started_by_t2: bool | None

    rt_dose_gy: float | None
    rt_fractions: int | None

    rtdose_t0_available: bool | None
    rtdose_t1_available: bool | None
    rtdose_t2_available: bool | None

    gtv_type_t0: str | None
    gtv_type_t1: str | None
    gtv_type_t2: str | None


def _latest_matching_file(
    root: Path,
    pattern: str,
) -> Path:
    matches = sorted(
        root.glob(pattern)
    )

    if not matches:
        raise FileNotFoundError(
            f"No metadata file matches {pattern!r} in {root}"
        )

    return matches[-1]


def _is_missing(
    value: Any,
) -> bool:
    return bool(
        pd.isna(value)
    )


def _optional_float(
    value: Any,
) -> float | None:
    if _is_missing(value):
        return None

    return float(value)


def _optional_int(
    value: Any,
) -> int | None:
    if _is_missing(value):
        return None

    numeric = float(value)
    rounded = round(numeric)

    if abs(numeric - rounded) > 1e-9:
        raise ValueError(
            "Expected integer-like value, "
            f"got {numeric}"
        )

    return int(rounded)


def _optional_str(
    value: Any,
) -> str | None:
    if _is_missing(value):
        return None

    text = str(value).strip()

    if not text:
        return None

    return text


def _required_str(
    value: Any,
    *,
    name: str,
) -> str:
    result = _optional_str(value)

    if result is None:
        raise ValueError(
            f"{name} must not be missing"
        )

    return result


def _availability(
    value: Any,
) -> bool:
    if _is_missing(value):
        raise ValueError(
            "Availability value must not be missing"
        )

    numeric = float(value)

    if numeric not in (0.0, 1.0):
        raise ValueError(
            "Availability value must be 0 or 1"
        )

    return bool(
        int(numeric)
    )


class CFBTreatmentMetadata:
    def __init__(
        self,
        metadata_root: Path,
    ) -> None:
        self.metadata_root = metadata_root

        treatment_path = _latest_matching_file(
            metadata_root,
            "CFB-GBM_treatment_data_*.tsv",
        )

        imaging_path = _latest_matching_file(
            metadata_root,
            (
                "CFB-GBM_treatment_"
                "imaging_availability_*.tsv"
            ),
        )

        self._treatment = pd.read_csv(
            treatment_path,
            sep="\t",
        )

        self._imaging = pd.read_csv(
            imaging_path,
            sep="\t",
        )

        missing_treatment = (
            _TREATMENT_COLUMNS
            - set(self._treatment.columns)
        )

        if missing_treatment:
            names = ", ".join(
                sorted(missing_treatment)
            )

            raise ValueError(
                "Treatment metadata is missing "
                f"columns: {names}"
            )

        missing_imaging = (
            _IMAGING_COLUMNS
            - set(self._imaging.columns)
        )

        if missing_imaging:
            names = ", ".join(
                sorted(missing_imaging)
            )

            raise ValueError(
                "Treatment imaging metadata is "
                f"missing columns: {names}"
            )

    def treatment(
        self,
        patient_id: int,
    ) -> TreatmentRecord | None:
        rows = self._treatment[
            self._treatment["id_patient"]
            == patient_id
        ]

        if rows.empty:
            return None

        if len(rows) != 1:
            raise ValueError(
                f"Patient {patient_id} has "
                f"{len(rows)} treatment rows"
            )

        row = rows.iloc[0]

        return TreatmentRecord(
            patient_id=patient_id,
            delay_t0_to_radiotherapy_weeks=(
                _optional_float(
                    row[
                        "delay_t0_to_radiotherapy "
                        "(weeks)"
                    ]
                )
            ),
            dose_gy=_optional_float(
                row["dose (Gy)"]
            ),
            fractions_number=_optional_int(
                row["fractions_number"]
            ),
        )

    def imaging_records(
        self,
        patient_id: int,
    ) -> tuple[TreatmentImagingRecord, ...]:
        rows = self._imaging[
            self._imaging["id_patient"]
            == patient_id
        ]

        records: list[
            TreatmentImagingRecord
        ] = []

        for _, row in rows.iterrows():
            temporality = _required_str(
                row["temporality"],
                name="temporality",
            )

            records.append(
                TreatmentImagingRecord(
                    patient_id=patient_id,
                    temporality=temporality,
                    gtv_available=_availability(
                        row["gtv"]
                    ),
                    gtv_type=_optional_str(
                        row["gtv_type"]
                    ),
                    rtdose_available=_availability(
                        row["rtdose"]
                    ),
                    treatment_machine=(
                        _optional_str(
                            row["treatment_machine"]
                        )
                    ),
                    tps=_optional_str(
                        row["tps"]
                    ),
                )
            )

        return tuple(records)

    def patient_context(
        self,
        patient_id: int,
        *,
        dt01_days: float,
        dt12_days: float,
    ) -> PatientTreatmentContext:
        if dt01_days <= 0:
            raise ValueError(
                "dt01_days must be positive"
            )

        if dt12_days <= 0:
            raise ValueError(
                "dt12_days must be positive"
            )

        treatment = self.treatment(
            patient_id
        )

        imaging = self.imaging_records(
            patient_id
        )

        by_timepoint = {
            record.temporality: record
            for record in imaging
        }

        if len(by_timepoint) != len(imaging):
            raise ValueError(
                f"Patient {patient_id} has "
                "duplicate imaging temporality rows"
            )

        if treatment is None:
            rt_start_day = None
            dose = None
            fractions = None
        else:
            rt_start_day = (
                treatment.radiotherapy_start_day
            )
            dose = treatment.dose_gy
            fractions = (
                treatment.fractions_number
            )

        total_days = (
            dt01_days
            + dt12_days
        )

        if rt_start_day is None:
            rt_start_phase = "unknown"
            rt_started_by_t1 = None
            rt_started_by_t2 = None

        elif rt_start_day <= 0:
            rt_start_phase = (
                "before_or_at_t0"
            )
            rt_started_by_t1 = True
            rt_started_by_t2 = True

        elif rt_start_day <= dt01_days:
            rt_start_phase = "t0_t1"
            rt_started_by_t1 = True
            rt_started_by_t2 = True

        elif rt_start_day <= total_days:
            rt_start_phase = "t1_t2"
            rt_started_by_t1 = False
            rt_started_by_t2 = True

        else:
            rt_start_phase = "after_t2"
            rt_started_by_t1 = False
            rt_started_by_t2 = False

        t0_record = by_timepoint.get(
            "t0"
        )

        t1_record = by_timepoint.get(
            "t1"
        )

        t2_record = by_timepoint.get(
            "t2"
        )

        return PatientTreatmentContext(
            patient_id=patient_id,
            has_treatment_record=(
                treatment is not None
            ),
            rt_start_day=rt_start_day,
            rt_start_phase=rt_start_phase,
            rt_started_by_t1=(
                rt_started_by_t1
            ),
            rt_started_by_t2=(
                rt_started_by_t2
            ),
            rt_dose_gy=dose,
            rt_fractions=fractions,
            rtdose_t0_available=(
                None
                if t0_record is None
                else t0_record.rtdose_available
            ),
            rtdose_t1_available=(
                None
                if t1_record is None
                else t1_record.rtdose_available
            ),
            rtdose_t2_available=(
                None
                if t2_record is None
                else t2_record.rtdose_available
            ),
            gtv_type_t0=(
                None
                if t0_record is None
                else t0_record.gtv_type
            ),
            gtv_type_t1=(
                None
                if t1_record is None
                else t1_record.gtv_type
            ),
            gtv_type_t2=(
                None
                if t2_record is None
                else t2_record.gtv_type
            ),
        )