from pathlib import Path
from types import SimpleNamespace

import pytest

import gbm_twin.workflows.patient_catalog as catalog_module
from gbm_twin.workflows.patient_catalog import (
    discover_patient_ids,
    get_patient_catalog_summary,
)


def test_discover_patient_ids(
    tmp_path: Path,
) -> None:
    patients_root = (
        tmp_path / "patients"
    )

    patients_root.mkdir()

    (
        patients_root
        / "Patient_8"
    ).mkdir()

    (
        patients_root
        / "patient-42"
    ).mkdir()

    (
        patients_root
        / "108"
    ).mkdir()

    (
        patients_root
        / "notes"
    ).mkdir()

    result = discover_patient_ids(
        patients_root
    )

    assert result == (
        8,
        42,
        108,
    )


def test_patient_catalog_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    timepoints = {
        "t0": SimpleNamespace(
            name="t0",
            days_from_baseline=0,
        ),
        "t1": SimpleNamespace(
            name="t1",
            days_from_baseline=98,
        ),
        "t2": SimpleNamespace(
            name="t2",
            days_from_baseline=252,
        ),
    }

    class FakePatient:
        def get_timepoint(
            self,
            name: str,
        ):
            if name not in timepoints:
                raise KeyError(name)

            return timepoints[name]

    class FakeMetadata:
        def __init__(
            self,
            metadata_root: Path,
        ) -> None:
            self.metadata_root = (
                metadata_root
            )

        def patient(
            self,
            patient_id: int,
        ):
            assert patient_id == 108
            return FakePatient()

    treatment_record = SimpleNamespace(
        radiotherapy_start_day=14.0,
        dose_gy=60.0,
        fractions_number=30,
    )

    treatment_context = SimpleNamespace(
        has_treatment_record=True,
        rt_start_day=14.0,
        rt_start_phase="between_t0_t1",
        rt_started_by_t1=True,
        rt_started_by_t2=True,
        rt_dose_gy=60.0,
        rt_fractions=30,
    )

    imaging = (
        SimpleNamespace(
            temporality="t0",
            gtv_available=True,
            gtv_type="manual",
            rtdose_available=False,
        ),
        SimpleNamespace(
            temporality="t1",
            gtv_available=True,
            gtv_type="manual",
            rtdose_available=False,
        ),
        SimpleNamespace(
            temporality="t2",
            gtv_available=True,
            gtv_type="manual",
            rtdose_available=False,
        ),
    )

    class FakeTreatmentMetadata:
        def __init__(
            self,
            metadata_root: Path,
        ) -> None:
            self.metadata_root = (
                metadata_root
            )

        def treatment(
            self,
            patient_id: int,
        ):
            assert patient_id == 108
            return treatment_record

        def imaging_records(
            self,
            patient_id: int,
        ):
            assert patient_id == 108
            return imaging

        def patient_context(
            self,
            patient_id: int,
            *,
            dt01_days: float,
            dt12_days: float,
        ):
            assert patient_id == 108
            assert dt01_days == 98.0
            assert dt12_days == 154.0

            return treatment_context

    monkeypatch.setattr(
        catalog_module,
        "CFBMetadata",
        FakeMetadata,
    )

    monkeypatch.setattr(
        catalog_module,
        "CFBTreatmentMetadata",
        FakeTreatmentMetadata,
    )

    result = (
        get_patient_catalog_summary(
            metadata_root=tmp_path,
            patient_id=108,
        )
    )

    assert result.patient_id == 108
    assert result.timepoint_count == 3

    assert result.dt01_days == 98.0
    assert result.dt12_days == 154.0

    assert (
        result.treatment.rt_start_day
        == 14.0
    )

    assert result.treatment.dose_gy == 60.0
    assert result.treatment.fractions == 30

    assert (
        result.treatment.reconstructable
        is True
    )


def test_discover_patient_ids_missing_root(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError
    ):
        discover_patient_ids(
            tmp_path / "missing"
        )