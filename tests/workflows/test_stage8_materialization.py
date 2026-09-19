from __future__ import annotations

from pathlib import Path

import pytest

from gbm_twin.workflows.stage8_materialization import (
    build_stage8_materialization_plan,
    resolve_stage8_source_data_root,
)


def _write_core_source(
    root: Path,
    *,
    patient_id: int,
) -> None:
    for timepoint in ("t0", "t1", "t2"):
        directory = root / str(patient_id) / timepoint
        directory.mkdir(parents=True, exist_ok=True)
        prefix = f"{patient_id}_{timepoint}"

        for suffix in ("t1gd", "gtv", "brain_mask"):
            (directory / f"{prefix}_{suffix}.nii.gz").write_bytes(b"nifti")


def test_materialization_plan_uses_official_cfb_layout(
    tmp_path: Path,
) -> None:
    source = tmp_path / "data"
    destination = tmp_path / "patients"
    _write_core_source(source, patient_id=5)

    plan = build_stage8_materialization_plan(
        source_root=source,
        destination_root=destination,
        patient_ids=(5,),
        require_spatial_rtdose=False,
    )

    assert len(plan) == 9
    assert plan[0].source_path == (
        source / "5" / "t0" / "5_t0_t1gd.nii.gz"
    )
    assert plan[0].destination_path == (
        destination / "5" / "t0" / "5_t0_t1gd.nii.gz"
    )


def test_materialization_plan_adds_rtdose_for_spatial_candidate(
    tmp_path: Path,
) -> None:
    source = tmp_path / "data"
    destination = tmp_path / "patients"
    _write_core_source(source, patient_id=7)

    dose = source / "7" / "rt" / "7_RTDOSE.nii.gz"
    dose.parent.mkdir(parents=True)
    dose.write_bytes(b"dose")

    plan = build_stage8_materialization_plan(
        source_root=source,
        destination_root=destination,
        patient_ids=(7,),
        require_spatial_rtdose=True,
    )

    assert len(plan) == 10
    assert plan[-1].input_name == "RTDOSE"
    assert plan[-1].source_path == dose.resolve()


def test_source_root_defaults_to_sibling_data_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GBM_TWIN_CFB_SOURCE_DATA_ROOT", raising=False)
    monkeypatch.delenv("GBM_TWIN_CFB_ROOT", raising=False)

    patients = tmp_path / "CFB-GBM" / "patients"

    assert resolve_stage8_source_data_root(
        explicit=None,
        patients_root=patients,
    ) == (tmp_path / "CFB-GBM" / "data").resolve()
