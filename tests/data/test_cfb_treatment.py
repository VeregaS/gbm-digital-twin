from pathlib import Path

from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)


def test_load_treatment_context(
    tmp_path: Path,
) -> None:
    treatment_path = (
        tmp_path
        / "CFB-GBM_treatment_data_v01.tsv"
    )

    treatment_path.write_text(
        (
            "id_patient\t"
            "delay_t0_to_radiotherapy (weeks)\t"
            "dose (Gy)\t"
            "fractions_number\n"
            "1\t3\t60\t30\n"
            "2\t\t\t\n"
        ),
        encoding="utf-8",
    )

    imaging_path = (
        tmp_path
        / (
            "CFB-GBM_treatment_"
            "imaging_availability_v01.tsv"
        )
    )

    imaging_path.write_text(
        (
            "id_patient\t"
            "temporality\t"
            "gtv\t"
            "gtv_type\t"
            "rtdose\t"
            "treatment_machine\t"
            "tps\n"
            "1\tt0\t1\t"
            "humanSegmentation\t"
            "1\tT1\tPRECISION\n"
            "1\tt1\t1\t"
            "genSegmentation\t"
            "0\t\t\n"
            "1\tt2\t1\t"
            "genSegmentation\t"
            "0\t\t\n"
            "2\tt0\t1\t"
            "humanSegmentation\t"
            "0\t\t\n"
        ),
        encoding="utf-8",
    )

    metadata = CFBTreatmentMetadata(
        tmp_path
    )

    context = metadata.patient_context(
        1,
        dt01_days=30.0,
        dt12_days=60.0,
    )

    assert context.has_treatment_record
    assert context.rt_start_day == 21.0
    assert context.rt_start_phase == "t0_t1"

    assert (
        context.rt_started_by_t1
        is True
    )

    assert (
        context.rt_started_by_t2
        is True
    )

    assert context.rt_dose_gy == 60.0
    assert context.rt_fractions == 30

    assert (
        context.rtdose_t0_available
        is True
    )

    assert (
        context.rtdose_t1_available
        is False
    )

    assert (
        context.gtv_type_t0
        == "humanSegmentation"
    )

    assert (
        context.gtv_type_t1
        == "genSegmentation"
    )


def test_unknown_treatment_timing(
    tmp_path: Path,
) -> None:
    treatment_path = (
        tmp_path
        / "CFB-GBM_treatment_data_v01.tsv"
    )

    treatment_path.write_text(
        (
            "id_patient\t"
            "delay_t0_to_radiotherapy (weeks)\t"
            "dose (Gy)\t"
            "fractions_number\n"
            "2\t\t\t\n"
        ),
        encoding="utf-8",
    )

    imaging_path = (
        tmp_path
        / (
            "CFB-GBM_treatment_"
            "imaging_availability_v01.tsv"
        )
    )

    imaging_path.write_text(
        (
            "id_patient\t"
            "temporality\t"
            "gtv\t"
            "gtv_type\t"
            "rtdose\t"
            "treatment_machine\t"
            "tps\n"
            "2\tt0\t1\t"
            "humanSegmentation\t"
            "0\t\t\n"
        ),
        encoding="utf-8",
    )

    metadata = CFBTreatmentMetadata(
        tmp_path
    )

    context = metadata.patient_context(
        2,
        dt01_days=70.0,
        dt12_days=70.0,
    )

    assert context.has_treatment_record
    assert context.rt_start_day is None
    assert context.rt_start_phase == "unknown"

    assert (
        context.rt_started_by_t1
        is None
    )

    assert (
        context.rt_started_by_t2
        is None
    )