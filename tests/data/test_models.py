from gbm_twin.data.models import Patient, Timepoint


def test_patient_can_store_timepoint() -> None:
    patient = Patient(patient_id="P001")

    t0 = Timepoint(
        name="t0",
        days_from_baseline=0,
    )

    patient.add_timepoint(t0)

    assert patient.get_timepoint("t0") == t0


def test_patient_rejects_duplicate_timepoint() -> None:
    patient = Patient(patient_id="P001")

    patient.add_timepoint(Timepoint(name="t0"))

    try:
        patient.add_timepoint(Timepoint(name="t0"))
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for duplicate timepoint")