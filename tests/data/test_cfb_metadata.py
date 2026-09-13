from pathlib import Path

import pandas as pd

from gbm_twin.data.cfb_metadata import CFBMetadata


def create_test_metadata(metadata_dir: Path) -> None:
    mri = pd.DataFrame(
        [
            {
                "id_patient": 1,
                "temporality": "t0",
                "time_diff_t0 (weeks)": 0,
            },
            {
                "id_patient": 1,
                "temporality": "t1",
                "time_diff_t0 (weeks)": 12,
            },
            {
                "id_patient": 1,
                "temporality": "t2",
                "time_diff_t0 (weeks)": 25,
            },
            {
                "id_patient": 2,
                "temporality": "t0",
                "time_diff_t0 (weeks)": 0,
            },
            {
                "id_patient": 2,
                "temporality": "t1",
                "time_diff_t0 (weeks)": 10,
            },
        ]
    )

    rano = pd.DataFrame(
        [
            {
                "id_patient": 1,
                "size_t0 (cm3)": 10.0,
                "size_t1 (cm3)": 12.0,
                "size_t2 (cm3)": 15.0,
            },
            {
                "id_patient": 2,
                "size_t0 (cm3)": 20.0,
                "size_t1 (cm3)": 22.0,
                "size_t2 (cm3)": None,
            },
        ]
    )

    mri.to_csv(
        metadata_dir / "CFB-GBM_mri_availability_test.tsv",
        sep="\t",
        index=False,
    )

    rano.to_csv(
        metadata_dir / "CFB-GBM_rano_criteria_test.tsv",
        sep="\t",
        index=False,
    )


def test_patient_ids(tmp_path: Path) -> None:
    create_test_metadata(tmp_path)

    metadata = CFBMetadata(tmp_path)

    assert metadata.patient_ids() == [1, 2]


def test_longitudinal_patients(tmp_path: Path) -> None:
    create_test_metadata(tmp_path)

    metadata = CFBMetadata(tmp_path)

    assert metadata.longitudinal_patients() == [1]


def test_prediction_cohort(tmp_path: Path) -> None:
    create_test_metadata(tmp_path)

    metadata = CFBMetadata(tmp_path)

    assert metadata.prediction_cohort() == [1]
    
def test_patient_timeline(tmp_path: Path) -> None:
    create_test_metadata(tmp_path)

    metadata = CFBMetadata(tmp_path)

    timeline = metadata.patient_timeline(1)

    assert [timepoint.name for timepoint in timeline] == ["t0", "t1", "t2"]

    assert [timepoint.days_from_baseline for timepoint in timeline] == [
        0,
        84,
        175,
    ]
    
def test_metadata_builds_patient(tmp_path: Path) -> None:
    create_test_metadata(tmp_path)

    metadata = CFBMetadata(tmp_path)
    patient = metadata.patient(1)

    assert patient.patient_id == "1"
    assert patient.interval_days("t0", "t1") == 84
    assert patient.interval_days("t1", "t2") == 91