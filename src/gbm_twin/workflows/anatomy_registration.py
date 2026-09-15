from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

import nibabel as nib
import numpy as np

from gbm_twin.anatomy.registration import (
    DEFAULT_REGISTRATION_CONFIG,
    RegistrationConfig,
    RegistrationResult,
    register_atlas_to_patient,
)
from gbm_twin.anatomy.registration_mask import (
    clean_registration_mask,
)
from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    prepare_patient_timepoint,
)


def _save_float_volume(
    *,
    data: np.ndarray,
    affine: np.ndarray,
    path: Path,
) -> None:
    image = nib.Nifti1Image(
        np.asarray(
            data,
            dtype=np.float32,
        ),
        np.asarray(
            affine,
            dtype=np.float64,
        ),
    )

    nib.save(
        image,
        str(path),
    )


def _save_binary_volume(
    *,
    data: np.ndarray,
    affine: np.ndarray,
    path: Path,
) -> None:
    image = nib.Nifti1Image(
        np.asarray(
            data,
            dtype=np.uint8,
        ),
        np.asarray(
            affine,
            dtype=np.float64,
        ),
    )

    nib.save(
        image,
        str(path),
    )


def _invalidate_previous_review(
    output_dir: Path,
) -> None:
    stale_files = (
        "labels.nii.gz",
        "labels_candidate.nii.gz",
        "review.json",
        "registration.json",
        "registration_qc.png",
        "linear_atlas_to_patient.tfm",
        "deformable_patient_grid.tfm",
        "atlas_template_registered.nii.gz",
        "atlas_brain_mask_registered.nii.gz",
        "atlas_template_linear.nii.gz",
        "atlas_brain_mask_linear.nii.gz",
        "labels_linear.nii.gz",
        "atlas_template_deformable.nii.gz",
        "atlas_brain_mask_deformable.nii.gz",
        "labels_deformable.nii.gz",
    )

    for filename in stale_files:
        (
            output_dir
            / filename
        ).unlink(
            missing_ok=True
        )


def prepare_patient_registered_atlas(
    *,
    metadata_root: Path,
    patients_root: Path,
    atlas_root: Path,
    patient_id: int,
    timepoint_name: str,
    target_spacing: tuple[
        float,
        float,
        float,
    ] = DEFAULT_TARGET_SPACING,
    config: RegistrationConfig = (
        DEFAULT_REGISTRATION_CONFIG
    ),
) -> RegistrationResult:
    normalized_timepoint = (
        timepoint_name
        .strip()
        .lower()
    )

    if normalized_timepoint not in {
        "t0",
        "t1",
        "t2",
    }:
        raise ValueError(
            "timepoint_name must "
            "be t0, t1 or t2"
        )

    if patient_id <= 0:
        raise ValueError(
            "patient_id must be positive"
        )

    metadata_root = (
        metadata_root.resolve()
    )

    patients_root = (
        patients_root.resolve()
    )

    atlas_root = (
        atlas_root.resolve()
    )

    template_path = (
        atlas_root
        / "template_t1.nii.gz"
    )

    atlas_brain_mask_path = (
        atlas_root
        / "template_brain_mask.nii.gz"
    )

    labelmap_path = (
        atlas_root
        / "template_labels.nii.gz"
    )

    manifest_path = (
        atlas_root
        / "manifest.json"
    )

    for path in (
        template_path,
        atlas_brain_mask_path,
        labelmap_path,
        manifest_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(
                "Atlas bootstrap is "
                "incomplete. Missing: "
                f"{path}"
            )

    prepared = (
        prepare_patient_timepoint(
            metadata_root=(
                metadata_root
            ),
            patients_root=(
                patients_root
            ),
            patient_id=(
                patient_id
            ),
            timepoint_name=(
                normalized_timepoint
            ),
            target_spacing=(
                target_spacing
            ),
        )
    )

    t1_affine = np.asarray(
        prepared.t1gd.affine,
        dtype=np.float64,
    )

    brain_affine = np.asarray(
        prepared.brain_mask.affine,
        dtype=np.float64,
    )

    if (
        prepared.t1gd.data.shape
        != prepared.brain_mask.data.shape
    ):
        raise ValueError(
            "Prepared T1Gd and brain "
            "mask shapes do not match"
        )

    if not np.allclose(
        t1_affine,
        brain_affine,
        rtol=0.0,
        atol=1e-5,
    ):
        raise ValueError(
            "Prepared T1Gd and brain "
            "mask affines do not match"
        )

    original_brain_mask = (
        np.asarray(
            prepared
            .brain_mask
            .data
        )
        > 0.5
    )

    mask_result = (
        clean_registration_mask(
            original_brain_mask
        )
    )

    output_dir = (
        atlas_root
        / "patients"
        / str(
            patient_id
        )
        / normalized_timepoint
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    _invalidate_previous_review(
        output_dir
    )

    persistent_registration_mask = (
        output_dir
        / (
            "patient_registration_"
            "mask.nii.gz"
        )
    )

    _save_binary_volume(
        data=(
            mask_result.mask
        ),
        affine=(
            brain_affine
        ),
        path=(
            persistent_registration_mask
        ),
    )

    mask_report_path = (
        output_dir
        / "registration_mask.json"
    )

    mask_report_path.write_text(
        json.dumps(
            asdict(
                mask_result.report
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with TemporaryDirectory(
        prefix="gbm-twin-atlas-"
    ) as temporary_directory:
        temporary_root = Path(
            temporary_directory
        )

        fixed_t1_path = (
            temporary_root
            / "patient_t1.nii.gz"
        )

        _save_float_volume(
            data=(
                prepared.t1gd.data
            ),
            affine=(
                t1_affine
            ),
            path=(
                fixed_t1_path
            ),
        )

        return register_atlas_to_patient(
            fixed_t1_path=(
                fixed_t1_path
            ),
            fixed_registration_mask_path=(
                persistent_registration_mask
            ),
            atlas_template_path=(
                template_path
            ),
            atlas_brain_mask_path=(
                atlas_brain_mask_path
            ),
            atlas_labelmap_path=(
                labelmap_path
            ),
            output_dir=(
                output_dir
            ),
            patient_id=(
                patient_id
            ),
            timepoint_name=(
                normalized_timepoint
            ),
            config=config,
        )