from __future__ import annotations

import json
from pathlib import Path

from gbm_twin.workflows.stage8_data_audit import (
    audit_stage8_cohort,
    load_sealed_stage8_data_audit,
)


def _write_protocol(path: Path) -> None:
    path.write_text(
        """schema_version: 1
exposed_development_patient_ids: [1]
holdout_fraction: 0.5
split_seed: 7
required_timepoints: [t0, t1, t2]
required_modalities: [t1gd]
preferred_modalities: [flair, dwi]
require_complete_rt_schedule: true
require_rtdose: true
observation_model:
  enhancing_detection_threshold: 0.80
  infiltrative_detection_threshold: 0.16
  transition_width_mm: 4.0
radiobiology:
  alpha_beta_ratio_gy: 10.0
  legacy_alpha_per_gy: 0.01
  reference_alpha_per_gy: 0.12
  effective_alpha_candidates_per_gy: [0.01, 0.10, 0.12, 0.14]
chemotherapy:
  enabled: false
treatment_memory:
  enabled: true
  proliferation_survival_candidates: [1.0, 0.99]
""",
        encoding="utf-8",
    )


def _write_metadata(root: Path) -> None:
    root.mkdir(parents=True)

    mri_lines = [
        "id_patient\ttemporality\tt1gd\tflair\tdwi",
    ]
    for patient_id in (1, 2, 3, 4):
        for timepoint in ("t0", "t1", "t2"):
            flair = 1 if patient_id in (1, 2) else 0
            dwi = 1 if patient_id == 2 else 0
            mri_lines.append(
                f"{patient_id}\t{timepoint}\t1\t{flair}\t{dwi}"
            )

    (root / "CFB-GBM_mri_availability_test.tsv").write_text(
        "\n".join(mri_lines) + "\n",
        encoding="utf-8",
    )

    treatment_lines = [
        "id_patient\tdelay_t0_to_radiotherapy (weeks)\tdose (Gy)\tfractions_number",
    ]
    for patient_id in (1, 2, 3, 4):
        treatment_lines.append(f"{patient_id}\t2\t60\t30")

    (root / "CFB-GBM_treatment_data_test.tsv").write_text(
        "\n".join(treatment_lines) + "\n",
        encoding="utf-8",
    )

    imaging_lines = [
        "id_patient\ttemporality\tgtv\tgtv_type\trtdose\ttreatment_machine\ttps",
    ]
    for patient_id in (1, 2, 3, 4):
        for timepoint in ("t0", "t1", "t2"):
            rtdose = 1 if timepoint == "t0" else 0
            imaging_lines.append(
                f"{patient_id}\t{timepoint}\t1\tauto\t{rtdose}\tmachine\ttps"
            )

    (root / "CFB-GBM_treatment_imaging_availability_test.tsv").write_text(
        "\n".join(imaging_lines) + "\n",
        encoding="utf-8",
    )


def test_stage8_audit_builds_deterministic_untouched_holdout(
    tmp_path: Path,
) -> None:
    metadata_root = tmp_path / "metadata"
    _write_metadata(metadata_root)

    protocol_path = tmp_path / "stage8.yaml"
    _write_protocol(protocol_path)

    output = tmp_path / "audit"
    result = audit_stage8_cohort(
        metadata_root=metadata_root,
        protocol_config_path=protocol_path,
        output_dir=output,
    )

    summary = result.manifest["summary"]
    split = result.manifest["split"]
    assert isinstance(summary, dict)
    assert isinstance(split, dict)

    assert summary["patient_count"] == 4
    assert summary["core_eligible_count"] == 4
    assert summary["gtv_complete_count"] == 4

    # Patient 2 is the only mpMRI member, so the rare stratum is not consumed
    # by the final holdout. One of the two non-exposed T1Gd-only patients is.
    assert summary["untouched_holdout_count"] == 1

    holdout = split["untouched_holdout_patient_ids"]
    assert isinstance(holdout, list)
    assert 1 not in holdout
    assert 2 not in holdout
    assert len(holdout) == 1
    assert split["method"] == "deterministic_stratified_hash_v1"

    leakage = result.manifest["leakage_control"]
    assert isinstance(leakage, dict)
    assert leakage["rano_metadata_loaded"] is False
    assert leakage["t2_image_content_loaded"] is False
    assert leakage["split_uses_outcomes"] is False

    loaded = load_sealed_stage8_data_audit(output)
    assert loaded.manifest == result.manifest


def test_stage8_audit_rejects_tampering(tmp_path: Path) -> None:
    metadata_root = tmp_path / "metadata"
    _write_metadata(metadata_root)

    protocol_path = tmp_path / "stage8.yaml"
    _write_protocol(protocol_path)

    output = tmp_path / "audit"
    audit_stage8_cohort(
        metadata_root=metadata_root,
        protocol_config_path=protocol_path,
        output_dir=output,
    )

    manifest_path = output / "stage8_data_audit.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["summary"]["patient_count"] = 999
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    try:
        load_sealed_stage8_data_audit(output)
    except ValueError as exc:
        assert "checksum mismatch" in str(exc)
    else:
        raise AssertionError("tampered audit must be rejected")
