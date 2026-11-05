import json
from pathlib import Path

import numpy as np
import pytest

from gbm_twin.data.dataset_manifest import (
    CFBDatasetManifest,
)
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.provenance import (
    build_prediction_provenance,
    sha256_file,
    v2_calibration_config_sha256,
)

GIT_SHA = (
    "0123456789abcdef"
    "0123456789abcdef"
    "01234567"
)


def make_dataset_manifest() -> CFBDatasetManifest:
    return CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source="The Cancer Imaging Archive",
        license="CC BY 4.0",
        expected_subjects=264,
        metadata_patterns=(
            "CFB-GBM_mri_availability_*.tsv",
            "CFB-GBM_rano_criteria_*.tsv",
            (
                "CFB-GBM_treatment_"
                "imaging_availability_*.tsv"
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
                "{timepoint}_t1gd.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_gtv.nii.gz"
            ),
            (
                "{patient_id}_"
                "{timepoint}_brain_mask.nii.gz"
            ),
        ),
    )


def make_config(
    *,
    volume_weight: float = 0.5,
    refinement_rounds: int = 1,
    upper_boundary_expansion_factor: float = 0.5,
) -> V2CalibrationConfig:
    return V2CalibrationConfig(
        diffusion_values=(
            0.01,
            0.03,
            0.05,
        ),
        proliferation_values=(
            0.005,
            0.015,
            0.025,
        ),
        volume_weight=volume_weight,
        refinement_rounds=refinement_rounds,
        upper_boundary_expansion_factor=(
            upper_boundary_expansion_factor
        ),
    )


def write_input_file(
    root: Path,
    name: str,
    content: bytes,
) -> Path:
    path = root / name
    path.write_bytes(content)
    return path


def make_volume(
    path: Path,
) -> NiftiVolume:
    return NiftiVolume(
        path=path,
        data=np.zeros(
            (2, 2, 2),
            dtype=np.float32,
        ),
        affine=np.eye(
            4,
            dtype=np.float64,
        ),
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )


def make_timepoint(
    root: Path,
    *,
    name: str,
    day: float,
) -> PreparedPatientTimepoint:
    t1gd_path = write_input_file(
        root,
        f"{name}_t1gd.nii.gz",
        f"{name}-t1gd".encode(),
    )

    gtv_path = write_input_file(
        root,
        f"{name}_gtv.nii.gz",
        f"{name}-gtv".encode(),
    )

    brain_path = write_input_file(
        root,
        f"{name}_brain_mask.nii.gz",
        f"{name}-brain".encode(),
    )

    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=make_volume(
            t1gd_path
        ),
        gtv=make_volume(
            gtv_path
        ),
        brain_mask=make_volume(
            brain_path
        ),
    )


def test_sha256_file_is_deterministic(
    tmp_path: Path,
) -> None:
    path = write_input_file(
        tmp_path,
        "input.bin",
        b"gbm-digital-twin",
    )

    first = sha256_file(path)
    second = sha256_file(path)

    assert first == second
    assert len(first) == 64


def test_config_checksum_changes_with_scientific_config(
) -> None:
    first = v2_calibration_config_sha256(
        make_config(
            volume_weight=0.5
        )
    )

    second = v2_calibration_config_sha256(
        make_config(
            volume_weight=0.75
        )
    )

    assert first != second


def test_config_checksum_changes_with_refinement_strategy(
) -> None:
    baseline = v2_calibration_config_sha256(
        make_config(
            refinement_rounds=1,
            upper_boundary_expansion_factor=0.5,
        )
    )

    accuracy_v1 = v2_calibration_config_sha256(
        make_config(
            refinement_rounds=3,
            upper_boundary_expansion_factor=1.0,
        )
    )

    assert baseline != accuracy_v1


def test_prediction_provenance_contains_only_logical_input_names(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        tmp_path,
        name="t0",
        day=0.0,
    )

    t1 = make_timepoint(
        tmp_path,
        name="t1",
        day=60.0,
    )

    provenance = build_prediction_provenance(
        dataset=make_dataset_manifest(),
        config=make_config(),
        start=t0,
        observed=t1,
        git_commit_sha=GIT_SHA,
        git_dirty=False,
    )

    payload = provenance.to_payload()

    assert payload["dataset_name"] == "CFB-GBM"
    assert payload["dataset_version"] == 4

    assert (
        payload["dataset_doi"]
        == "10.7937/v9pn-2f72"
    )

    assert (
        payload["git_commit_sha"]
        == GIT_SHA
    )

    assert payload["git_dirty"] is False

    logical_names = tuple(
        item["logical_name"]
        for item in payload["inputs"]
    )

    assert logical_names == (
        "t0_t1gd",
        "t0_gtv",
        "t0_brain_mask",
        "t1_t1gd",
        "t1_gtv",
        "t1_brain_mask",
    )

    serialized = json.dumps(
        payload,
        sort_keys=True,
    )

    assert (
        str(tmp_path.resolve())
        not in serialized
    )

    assert "t2" not in logical_names


def test_prediction_provenance_records_input_checksums(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        tmp_path,
        name="t0",
        day=0.0,
    )

    t1 = make_timepoint(
        tmp_path,
        name="t1",
        day=60.0,
    )

    provenance = build_prediction_provenance(
        dataset=make_dataset_manifest(),
        config=make_config(),
        start=t0,
        observed=t1,
        git_commit_sha=GIT_SHA,
        git_dirty=True,
    )

    payload = provenance.to_payload()

    checksums = {
        item["logical_name"]: item["sha256"]
        for item in payload["inputs"]
    }

    assert checksums["t0_gtv"] == (
        sha256_file(
            t0.gtv.path
        )
    )

    assert checksums["t1_gtv"] == (
        sha256_file(
            t1.gtv.path
        )
    )

    assert payload["git_dirty"] is True


def test_prediction_provenance_rejects_missing_input_file(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        tmp_path,
        name="t0",
        day=0.0,
    )

    t1 = make_timepoint(
        tmp_path,
        name="t1",
        day=60.0,
    )

    t1.gtv.path.unlink()

    with pytest.raises(
        FileNotFoundError,
        match="Provenance input file not found",
    ):
        build_prediction_provenance(
            dataset=make_dataset_manifest(),
            config=make_config(),
            start=t0,
            observed=t1,
            git_commit_sha=GIT_SHA,
            git_dirty=False,
        )


def test_prediction_provenance_rejects_invalid_git_sha(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        tmp_path,
        name="t0",
        day=0.0,
    )

    t1 = make_timepoint(
        tmp_path,
        name="t1",
        day=60.0,
    )

    with pytest.raises(
        ValueError,
        match="Git commit SHA",
    ):
        build_prediction_provenance(
            dataset=make_dataset_manifest(),
            config=make_config(),
            start=t0,
            observed=t1,
            git_commit_sha="not-a-sha",
            git_dirty=False,
        )


def test_prediction_provenance_rejects_different_patients(
    tmp_path: Path,
) -> None:
    t0 = make_timepoint(
        tmp_path,
        name="t0",
        day=0.0,
    )

    t1_original = make_timepoint(
        tmp_path,
        name="t1",
        day=60.0,
    )

    t1 = PreparedPatientTimepoint(
        patient_id=99,
        name=t1_original.name,
        days_from_baseline=(
            t1_original.days_from_baseline
        ),
        t1gd=t1_original.t1gd,
        gtv=t1_original.gtv,
        brain_mask=t1_original.brain_mask,
    )

    with pytest.raises(
        ValueError,
        match="different patients",
    ):
        build_prediction_provenance(
            dataset=make_dataset_manifest(),
            config=make_config(),
            start=t0,
            observed=t1,
            git_commit_sha=GIT_SHA,
            git_dirty=False,
        )
