from __future__ import annotations

from pathlib import Path

import pytest

from gbm_twin.data.dataset_manifest import (
    CFBDatasetManifest,
    load_cfb_dataset_manifest,
)


def _write_manifest(path: Path) -> None:
    path.write_text(
        """dataset:
  name: CFB-GBM
  version: 4
  updated: "2026-09-11"
  doi: "10.7937/v9pn-2f72"
  source: "The Cancer Imaging Archive"
  license: "CC BY 4.0"
  expected_subjects: 264
contract:
  metadata_patterns:
    - "CFB-GBM_mri_availability_*.tsv"
  required_timepoints:
    - t0
    - t1
    - t2
  required_modalities:
    - t1gd
  required_patient_files:
    - "{patient_id}_{timepoint}_t1gd.nii.gz"
    - "{patient_id}_{timepoint}_gtv.nii.gz"
    - "{patient_id}_{timepoint}_brain_mask.nii.gz"
""",
        encoding="utf-8",
    )


def test_load_cfb_dataset_manifest(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "cfb.yaml"
    )

    _write_manifest(
        path
    )

    manifest = (
        load_cfb_dataset_manifest(
            path
        )
    )

    assert manifest == CFBDatasetManifest(
        name="CFB-GBM",
        version=4,
        updated="2026-09-11",
        doi="10.7937/v9pn-2f72",
        source=(
            "The Cancer Imaging Archive"
        ),
        license="CC BY 4.0",
        expected_subjects=264,
        metadata_patterns=(
            "CFB-GBM_mri_availability_*.tsv",
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
            "{patient_id}_{timepoint}_t1gd.nii.gz",
            "{patient_id}_{timepoint}_gtv.nii.gz",
            "{patient_id}_{timepoint}_brain_mask.nii.gz",
        ),
    )


def test_manifest_rejects_file_template_without_timepoint(
) -> None:
    with pytest.raises(
        ValueError,
        match="timepoint",
    ):
        CFBDatasetManifest(
            name="CFB-GBM",
            version=4,
            updated="2026-09-11",
            doi="doi",
            source="source",
            license="license",
            expected_subjects=1,
            metadata_patterns=("*.tsv",),
            required_timepoints=("t0",),
            required_modalities=("t1gd",),
            required_patient_files=(
                "{patient_id}_t1gd.nii.gz",
            ),
        )
