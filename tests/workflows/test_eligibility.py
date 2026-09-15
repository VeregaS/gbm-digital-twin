from pathlib import Path

from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.dataset_manifest import (
    CFBDatasetManifest,
)
from gbm_twin.workflows.eligibility import (
    EligibilityReason,
    assess_patient_eligibility,
)


def make_manifest() -> (
    CFBDatasetManifest
):
    return CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source=(
            "The Cancer Imaging "
            "Archive"
        ),
        license="CC BY 4.0",
        expected_subjects=1,
        metadata_patterns=(
            (
                "CFB-GBM_"
                "mri_availability_*.tsv"
            ),
            (
                "CFB-GBM_"
                "rano_criteria_*.tsv"
            ),
            (
                "CFB-GBM_"
                "treatment_imaging_"
                "availability_*.tsv"
            ),
        ),
        required_timepoints=(
            "t0",
            "t1",
            "t2",
        ),
        required_modalities=(
            "t1gd",
        ),
        required_patient_files=(
            (
                "{patient_id}_"
                "{timepoint}_"
                "t1gd.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_"
                "gtv.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_"
                "brain_mask.nii.gz"
            ),
        ),
    )


def write_metadata(
    metadata_root: Path,
    *,
    include_t2: bool = True,
    t1_has_t1gd: bool = True,
    t2_week: float = 8.0,
) -> None:
    metadata_root.mkdir(
        parents=True
    )

    mri_rows = [
        (
            "id_patient\t"
            "temporality\t"
            "time_diff_t0 (weeks)\t"
            "t1gd"
        ),
        "42\tt0\t0\t1",
        (
            "42\tt1\t4\t"
            f"{1 if t1_has_t1gd else 0}"
        ),
    ]

    if include_t2:
        mri_rows.append(
            
                "42\tt2\t"
                f"{t2_week}\t1"
            
        )

    (
        metadata_root
        / (
            "CFB-GBM_"
            "mri_availability_test.tsv"
        )
    ).write_text(
        "\n".join(
            mri_rows
        )
        + "\n",
        encoding="utf-8",
    )

    (
        metadata_root
        / (
            "CFB-GBM_"
            "rano_criteria_test.tsv"
        )
    ).write_text(
        "\n".join(
            [
                (
                    "id_patient\t"
                    "size_t0 (cm3)\t"
                    "size_t1 (cm3)\t"
                    "size_t2 (cm3)"
                ),
                (
                    "42\t"
                    "1.0\t"
                    "1.2\t"
                    "1.4"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    treatment_rows = [
        (
            "id_patient\t"
            "temporality\t"
            "gtv_type"
        ),
        "42\tt0\tmanual",
        "42\tt1\tmanual",
    ]

    if include_t2:
        treatment_rows.append(
            "42\tt2\tmanual"
        )

    (
        metadata_root
        / (
            "CFB-GBM_"
            "treatment_imaging_"
            "availability_test.tsv"
        )
    ).write_text(
        "\n".join(
            treatment_rows
        )
        + "\n",
        encoding="utf-8",
    )


def write_prepared_patient(
    patients_root: Path,
    *,
    include_t2: bool = True,
) -> None:
    timepoints = [
        "t0",
        "t1",
    ]

    if include_t2:
        timepoints.append(
            "t2"
        )

    for timepoint_name in (
        timepoints
    ):
        directory = (
            patients_root
            / "42"
            / timepoint_name
        )

        directory.mkdir(
            parents=True
        )

        for suffix in (
            "t1gd",
            "gtv",
            "brain_mask",
        ):
            (
                directory
                / (
                    "42_"
                    f"{timepoint_name}_"
                    f"{suffix}.nii.gz"
                )
            ).touch()


def test_patient_is_eligible_when_contract_is_satisfied(
    tmp_path: Path,
) -> None:
    metadata_root = (
        tmp_path
        / "metadata"
    )

    patients_root = (
        tmp_path
        / "patients"
    )

    write_metadata(
        metadata_root
    )

    write_prepared_patient(
        patients_root
    )

    result = (
        assess_patient_eligibility(
            metadata=CFBMetadata(
                metadata_root
            ),
            manifest=make_manifest(),
            patients_root=(
                patients_root
            ),
            patient_id=42,
        )
    )

    assert result.eligible
    assert result.issues == ()
    assert result.reason_codes == ()


def test_unknown_patient_is_ineligible(
    tmp_path: Path,
) -> None:
    metadata_root = (
        tmp_path
        / "metadata"
    )

    patients_root = (
        tmp_path
        / "patients"
    )

    write_metadata(
        metadata_root
    )

    result = (
        assess_patient_eligibility(
            metadata=CFBMetadata(
                metadata_root
            ),
            manifest=make_manifest(),
            patients_root=(
                patients_root
            ),
            patient_id=99,
        )
    )

    assert not result.eligible

    assert result.reason_codes == (
        EligibilityReason
        .UNKNOWN_PATIENT
        .value,
    )


def test_missing_timepoint_has_explicit_reason(
    tmp_path: Path,
) -> None:
    metadata_root = (
        tmp_path
        / "metadata"
    )

    patients_root = (
        tmp_path
        / "patients"
    )

    write_metadata(
        metadata_root,
        include_t2=False,
    )

    write_prepared_patient(
        patients_root,
        include_t2=False,
    )

    result = (
        assess_patient_eligibility(
            metadata=CFBMetadata(
                metadata_root
            ),
            manifest=make_manifest(),
            patients_root=(
                patients_root
            ),
            patient_id=42,
        )
    )

    assert not result.eligible

    assert result.reason_codes == (
        EligibilityReason
        .MISSING_REQUIRED_TIMEPOINT
        .value,
    )


def test_missing_modality_has_explicit_reason(
    tmp_path: Path,
) -> None:
    metadata_root = (
        tmp_path
        / "metadata"
    )

    patients_root = (
        tmp_path
        / "patients"
    )

    write_metadata(
        metadata_root,
        t1_has_t1gd=False,
    )

    write_prepared_patient(
        patients_root
    )

    result = (
        assess_patient_eligibility(
            metadata=CFBMetadata(
                metadata_root
            ),
            manifest=make_manifest(),
            patients_root=(
                patients_root
            ),
            patient_id=42,
        )
    )

    assert not result.eligible

    assert result.reason_codes == (
        EligibilityReason
        .MISSING_REQUIRED_MODALITY
        .value,
    )


def test_missing_prepared_file_has_explicit_reason(
    tmp_path: Path,
) -> None:
    metadata_root = (
        tmp_path
        / "metadata"
    )

    patients_root = (
        tmp_path
        / "patients"
    )

    write_metadata(
        metadata_root
    )

    write_prepared_patient(
        patients_root
    )

    missing_path = (
        patients_root
        / "42"
        / "t1"
        / "42_t1_gtv.nii.gz"
    )

    missing_path.unlink()

    result = (
        assess_patient_eligibility(
            metadata=CFBMetadata(
                metadata_root
            ),
            manifest=make_manifest(),
            patients_root=(
                patients_root
            ),
            patient_id=42,
        )
    )

    assert not result.eligible

    assert result.reason_codes == (
        EligibilityReason
        .MISSING_PREPARED_FILE
        .value,
    )

    assert (
        str(
            missing_path
        )
        in result.issues[0].detail
    )


def test_invalid_time_interval_has_explicit_reason(
    tmp_path: Path,
) -> None:
    metadata_root = (
        tmp_path
        / "metadata"
    )

    patients_root = (
        tmp_path
        / "patients"
    )

    write_metadata(
        metadata_root,
        t2_week=3.0,
    )

    write_prepared_patient(
        patients_root
    )

    result = (
        assess_patient_eligibility(
            metadata=CFBMetadata(
                metadata_root
            ),
            manifest=make_manifest(),
            patients_root=(
                patients_root
            ),
            patient_id=42,
        )
    )

    assert not result.eligible

    assert result.reason_codes == (
        EligibilityReason
        .INVALID_TIME_INTERVAL
        .value,
    )