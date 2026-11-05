from __future__ import annotations

from pathlib import Path

from gbm_twin.workflows.stage8_validation import (
    _validation_patient_ids,
    preflight_stage8_validation_inputs,
)


def test_internal_validation_ids_exclude_exposed_and_holdout() -> None:
    manifest: dict[str, object] = {
        "patients": [
            {
                "patient_id": 1,
                "split": "development-exposed",
                "core_eligible": True,
                "exposed_development": True,
            },
            {
                "patient_id": 2,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 3,
                "split": "internal-validation",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 4,
                "split": "untouched-holdout",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 5,
                "split": "development",
                "core_eligible": False,
                "exposed_development": False,
            },
        ]
    }

    assert _validation_patient_ids(manifest) == (2, 3)


def _materialize_core_patient(
    root: Path,
    *,
    patient_id: int,
) -> None:
    for timepoint in ("t0", "t1", "t2"):
        directory = root / str(patient_id) / timepoint
        directory.mkdir(parents=True, exist_ok=True)
        prefix = f"{patient_id}_{timepoint}"

        for suffix in ("t1gd", "gtv", "brain_mask"):
            (directory / f"{prefix}_{suffix}.nii.gz").write_bytes(b"fixture")


def test_validation_preflight_reports_all_missing_core_inputs(
    tmp_path: Path,
) -> None:
    patients_root = tmp_path / "patients"
    _materialize_core_patient(
        patients_root,
        patient_id=7,
    )

    missing = (
        patients_root
        / "7"
        / "t1"
        / "7_t1_brain_mask.nii.gz"
    )
    missing.unlink()

    issues = preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=(7, 8),
        require_spatial_rtdose=False,
    )

    assert any(
        issue.patient_id == 7
        and issue.input_name == "t1 brain mask"
        and issue.expected_path == str(missing)
        for issue in issues
    )

    patient_8_issues = [
        issue
        for issue in issues
        if issue.patient_id == 8
    ]
    assert len(patient_8_issues) == 9


def test_validation_preflight_requires_rtdose_only_for_spatial_model(
    tmp_path: Path,
) -> None:
    patients_root = tmp_path / "patients"
    _materialize_core_patient(
        patients_root,
        patient_id=9,
    )

    uniform_issues = preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=(9,),
        require_spatial_rtdose=False,
    )
    spatial_issues = preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=(9,),
        require_spatial_rtdose=True,
    )

    assert uniform_issues == ()
    assert len(spatial_issues) == 1
    assert spatial_issues[0].patient_id == 9
    assert spatial_issues[0].input_name == "RTDOSE"

    dose = patients_root / "9" / "rt" / "9_rtdose.nii.gz"
    dose.parent.mkdir(parents=True)
    dose.write_bytes(b"fixture")

    assert preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=(9,),
        require_spatial_rtdose=True,
    ) == ()
