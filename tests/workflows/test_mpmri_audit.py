from __future__ import annotations

from pathlib import Path

from gbm_twin.workflows.mpmri_audit import _modality_present


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"test")


def test_modality_audit_recognizes_cfb_aliases(tmp_path: Path) -> None:
    patient_root = tmp_path / "8"
    _touch(patient_root / "t0" / "8_t0_t1gd.nii.gz")
    _touch(patient_root / "t0" / "flair" / "8_t0_flair.nii.gz")
    _touch(patient_root / "t0" / "dwi" / "8_t0_adc.nii.gz")

    assert _modality_present(
        patient_root,
        patient_id=8,
        timepoint="t0",
        modality="t1gd",
    )
    assert _modality_present(
        patient_root,
        patient_id=8,
        timepoint="t0",
        modality="flair",
    )
    assert _modality_present(
        patient_root,
        patient_id=8,
        timepoint="t0",
        modality="adc",
    )
    assert not _modality_present(
        patient_root,
        patient_id=8,
        timepoint="t0",
        modality="dwi",
    )


def test_modality_audit_accepts_t1eg_alias(tmp_path: Path) -> None:
    patient_root = tmp_path / "8"
    _touch(patient_root / "t1" / "8_t1_t1eg.nii.gz")

    assert _modality_present(
        patient_root,
        patient_id=8,
        timepoint="t1",
        modality="t1gd",
    )


def test_modality_audit_ignores_similar_unexpected_names(
    tmp_path: Path,
) -> None:
    patient_root = tmp_path / "8"
    _touch(patient_root / "t2" / "8_t2_adc_registered.nii.gz")

    assert not _modality_present(
        patient_root,
        patient_id=8,
        timepoint="t2",
        modality="adc",
    )
