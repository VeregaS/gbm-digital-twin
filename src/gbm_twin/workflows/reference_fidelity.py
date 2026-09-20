from __future__ import annotations

import json
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import cast

import numpy as np

from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.data.nifti import load_nifti
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.observation import latent_density_from_mri_detection
from gbm_twin.preprocessing.resampling import resample_volume_to_reference
from gbm_twin.reference.tumortwin import (
    TUMORTWIN_COMMIT,
    TumorTwinReferenceRequest,
    TumorTwinReferenceResult,
    reference_request_signature,
    run_external_tumortwin,
)
from gbm_twin.reference.tumortwin_cellularity import (
    tumortwin_adc_to_cellularity,
)
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.reference_benchmark import (
    ReferenceBenchmarkRow,
    _load_stage9_manifest,
    _observation_parameters,
    _stage9_patient_references,
    _summary,
    _write_csv,
)
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_patient import (
    Stage8ForecastInputs,
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage8_validation import (
    preflight_stage8_validation_inputs,
)
from gbm_twin.workflows.stage9_selection_artifact import (
    load_selected_stage9_model,
)

REFERENCE_FIDELITY_SCHEMA_VERSION = 1
GTV_ENGINE = "tumortwin-lm-roi"
ADC_ENGINE = "tumortwin-adc-lm-roi"


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return cast(dict[str, object], value)


def _load_mpmri_audit(
    path: Path,
) -> tuple[dict[int, dict[str, object]], dict[str, object]]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    root = _mapping(raw, name="mpMRI audit")

    patients = root.get("patients")
    if not isinstance(patients, list):
        raise ValueError("mpMRI audit patients must be a list")

    by_id: dict[int, dict[str, object]] = {}
    for raw_row in patients:
        row = _mapping(raw_row, name="mpMRI audit patient")
        patient_id = row.get("patient_id")
        if type(patient_id) is not int:
            raise ValueError("mpMRI audit patient_id must be integer")
        by_id[cast(int, patient_id)] = row

    return by_id, root


def _find_modality_file(
    patient_root: Path,
    *,
    patient_id: int,
    timepoint: str,
    modality: str,
) -> Path:
    timepoint_root = patient_root / timepoint
    expected_stem = f"{patient_id}_{timepoint}_{modality}".lower()

    matches: list[Path] = []
    if timepoint_root.is_dir():
        for path in timepoint_root.rglob("*"):
            if not path.is_file():
                continue
            name = path.name.lower()
            if name.endswith(".nii.gz"):
                stem = name[:-7]
            elif name.endswith(".nii"):
                stem = name[:-4]
            else:
                continue
            if stem == expected_stem:
                matches.append(path)

    if len(matches) != 1:
        raise FileNotFoundError(
            f"Patient {patient_id} {timepoint}: expected exactly one "
            f"{modality} NIfTI, found {len(matches)} under {timepoint_root}"
        )
    return matches[0]


def _adc_density(
    *,
    patients_root: Path,
    inputs: Stage8ForecastInputs,
    timepoint: str,
) -> np.ndarray:
    prepared = inputs.start if timepoint == "t0" else inputs.observed
    adc_path = _find_modality_file(
        patients_root / str(inputs.patient_id),
        patient_id=inputs.patient_id,
        timepoint=timepoint,
        modality="adc",
    )
    adc = resample_volume_to_reference(
        load_nifti(adc_path),
        prepared.t1gd,
        is_mask=False,
    )
    return tumortwin_adc_to_cellularity(
        adc.data,
        prepared.gtv.data > 0.5,
    )


def _roi_slices(
    support: np.ndarray,
    *,
    padding_voxels: int,
) -> tuple[slice, slice, slice]:
    mask = np.asarray(support, dtype=bool)
    if mask.ndim != 3:
        raise ValueError("ROI support must be 3D")
    if padding_voxels < 0:
        raise ValueError("ROI padding must be non-negative")

    coordinates = np.argwhere(mask)
    if coordinates.size == 0:
        raise ValueError("ROI support must contain at least one voxel")

    starts = np.maximum(coordinates.min(axis=0) - padding_voxels, 0)
    stops = np.minimum(
        coordinates.max(axis=0) + padding_voxels + 1,
        np.asarray(mask.shape),
    )
    slices = tuple(
        slice(int(start), int(stop))
        for start, stop in zip(starts, stops, strict=True)
    )
    result = cast(tuple[slice, slice, slice], slices)

    crop_shape = tuple(item.stop - item.start for item in result)
    if any(size < 3 for size in crop_shape):
        raise ValueError("TumorTwin ROI crop must be at least 3 voxels per axis")
    return result


def _crop(array: np.ndarray, roi: tuple[slice, slice, slice]) -> np.ndarray:
    return np.asarray(array[roi]).copy()


def _restore_prediction(
    prediction: np.ndarray,
    *,
    full_shape: tuple[int, ...],
    roi: tuple[slice, slice, slice],
) -> np.ndarray:
    restored = np.zeros(full_shape, dtype=np.float32)
    expected_shape = restored[roi].shape
    if prediction.shape != expected_shape:
        raise ValueError(
            "TumorTwin cropped prediction shape does not match ROI: "
            f"{prediction.shape} != {expected_shape}"
        )
    restored[roi] = prediction
    return restored


def _adc_eligible_patient_ids(
    patient_ids: tuple[int, ...],
    mpmri_rows: dict[int, dict[str, object]],
) -> tuple[int, ...]:
    result: list[int] = []
    for patient_id in patient_ids:
        row = mpmri_rows.get(patient_id, {})
        if row.get("t0_adc") is True and row.get("t1_adc") is True:
            result.append(patient_id)
    return tuple(result)


def _reference_request(
    *,
    patient_id: int,
    initial_density: np.ndarray,
    observed_density: np.ndarray,
    brain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    calibration_duration: float,
    forecast_duration: float,
    dt_days: float,
    fraction_days: tuple[float, ...],
    fraction_doses: tuple[float, ...],
    alpha_per_gy: float,
    alpha_beta_ratio_gy: float,
    optimizer_iterations: int,
) -> TumorTwinReferenceRequest:
    return TumorTwinReferenceRequest(
        patient_id=patient_id,
        initial_density=initial_density,
        observed_density=observed_density,
        brain_mask=brain_mask,
        spacing_mm=spacing,
        calibration_duration_days=calibration_duration,
        forecast_duration_days=forecast_duration,
        dt_days=dt_days,
        radiotherapy_fraction_days=fraction_days,
        radiotherapy_fraction_doses_gy=fraction_doses,
        alpha_per_gy=alpha_per_gy,
        alpha_beta_ratio_gy=alpha_beta_ratio_gy,
        mode="calibrate",
        diffusion_bounds=(0.0, 2.0),
        proliferation_bounds=(0.0, 0.5),
        optimizer_iterations=optimizer_iterations,
    )


def _evaluate_row(
    *,
    patient_id: int,
    engine: str,
    result: TumorTwinReferenceResult,
    prediction_density: np.ndarray,
    threshold: float,
    observed_t2: np.ndarray,
    persistence: np.ndarray,
    spacing: tuple[float, float, float],
    stage9_dice: float,
) -> ReferenceBenchmarkRow:
    predicted = np.asarray(prediction_density >= threshold, dtype=bool)
    persistence_dice = dice_score(persistence, observed_t2)
    score = dice_score(predicted, observed_t2)

    return ReferenceBenchmarkRow(
        patient_id=patient_id,
        engine=engine,
        diffusion=result.diffusion,
        proliferation=result.proliferation,
        dice=score,
        persistence_dice=persistence_dice,
        delta_vs_persistence=score - persistence_dice,
        relative_volume_error=relative_volume_error(
            predicted,
            observed_t2,
        ),
        hd95_mm=hausdorff95_mm(
            predicted,
            observed_t2,
            spacing=spacing,
        ),
        centroid_distance_mm=centroid_distance_mm(
            predicted,
            observed_t2,
            spacing=spacing,
        ),
        stage9_dice=stage9_dice,
        delta_vs_stage9=score - stage9_dice,
    )


def run_reference_fidelity_benchmark(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    stage8_selection_root: Path,
    stage9_selection_root: Path,
    mpmri_audit_path: Path,
    tumortwin_python: Path,
    worker_script: Path,
    cache_root: Path,
    output_dir: Path,
    roi_padding_voxels: int = 10,
    optimizer_iterations: int = 8,
    allow_dirty: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, object]:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Reference fidelity destination exists: {destination}"
        )
    if roi_padding_voxels < 0:
        raise ValueError("roi_padding_voxels must be non-negative")
    if optimizer_iterations < 1:
        raise ValueError("optimizer_iterations must be positive")

    repository = read_repository_state(repo_root.resolve())
    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Reference fidelity benchmark requires a clean Git working tree"
        )

    selected_stage8 = load_selected_stage8_model(stage8_selection_root)
    selected_stage9 = load_selected_stage9_model(stage9_selection_root)
    stage9_manifest, stage9_sha = _load_stage9_manifest(
        stage9_selection_root
    )
    if (
        selected_stage9.stage8_model_selection_sha256
        != selected_stage8.source_manifest_sha256
    ):
        raise ValueError("Stage 8 and Stage 9 artifacts are inconsistent")

    mpmri_rows, mpmri_manifest = _load_mpmri_audit(mpmri_audit_path)
    mpmri_source = _mapping(
        mpmri_manifest.get("source"),
        name="mpMRI audit source",
    )
    if (
        mpmri_source.get("stage8_data_audit_sha256")
        != selected_stage9.stage8_data_audit_sha256
    ):
        raise ValueError("mpMRI audit does not match the sealed Stage 8 audit")

    experiment = load_cohort_experiment_config(experiment_config_path)
    metadata_root = (
        experiment.metadata_root
        if experiment.metadata_root.is_absolute()
        else repo_root.resolve() / experiment.metadata_root
    )
    patients_root = (
        experiment.patients_root
        if experiment.patients_root.is_absolute()
        else repo_root.resolve() / experiment.patients_root
    )
    observation = _observation_parameters(stage8_protocol_path)
    treatment = CFBTreatmentMetadata(metadata_root)

    references = _stage9_patient_references(stage9_manifest)
    patient_ids = tuple(item.patient_id for item in references)
    issues = preflight_stage8_validation_inputs(
        patients_root=patients_root,
        patient_ids=patient_ids,
        require_spatial_rtdose=False,
    )
    if issues:
        preview = "\n".join(
            f"  patient {item.patient_id}: {item.input_name} -> "
            f"{item.expected_path}"
            for item in issues[:40]
        )
        raise FileNotFoundError(
            "Reference fidelity preflight failed before execution:\n"
            + preview
        )

    adc_patient_ids = _adc_eligible_patient_ids(
        patient_ids,
        mpmri_rows,
    )
    if not adc_patient_ids:
        raise ValueError(
            "No Stage 9 development patients have both t0 and t1 ADC locally"
        )

    for patient_id in adc_patient_ids:
        for timepoint in ("t0", "t1"):
            _find_modality_file(
                patients_root / str(patient_id),
                patient_id=patient_id,
                timepoint=timepoint,
                modality="adc",
            )

    rows: list[ReferenceBenchmarkRow] = []
    cache = cache_root.resolve()
    cache.mkdir(parents=True, exist_ok=True)

    for index, reference in enumerate(references, start=1):
        if progress is not None:
            progress(
                f"[reference-fidelity] patient {reference.patient_id} "
                f"({index}/{len(references)}): preparing pre-t2 inputs"
            )

        inputs = prepare_stage8_forecast_inputs(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=reference.patient_id,
            target_spacing=experiment.evaluation.target_spacing,
            treatment=treatment,
            observation_parameters=observation,
            load_spatial_rtdose=False,
            require_spatial_rtdose=False,
        )
        start_day = inputs.start.days_from_baseline
        observed_day = inputs.observed.days_from_baseline
        if not np.isclose(
            observed_day,
            reference.t1_day,
            rtol=0.0,
            atol=1e-6,
        ):
            raise ValueError(
                f"Patient {reference.patient_id}: Stage 9 t1 day mismatch"
            )

        forecast_duration = reference.t2_day - reference.t1_day
        if forecast_duration <= 0.0:
            raise ValueError(
                f"Patient {reference.patient_id}: invalid t1/t2 interval"
            )

        fraction_days: list[float] = []
        fraction_doses: list[float] = []
        for day in inputs.schedule.fraction_days:
            shifted = day - start_day
            if shifted >= 0.0:
                fraction_days.append(shifted)
                fraction_doses.append(
                    inputs.schedule.dose_per_fraction_gy
                )

        support = np.asarray(
            (inputs.start.gtv.data > 0.5)
            | (inputs.observed.gtv.data > 0.5),
            dtype=bool,
        )
        roi = _roi_slices(
            support,
            padding_voxels=roi_padding_voxels,
        )
        observed_density = latent_density_from_mri_detection(
            inputs.observed.gtv.data > 0.5,
            inputs.domain_mask,
            spacing=inputs.observed.spacing,
            parameters=observation,
        )

        requests: dict[str, TumorTwinReferenceRequest] = {
            GTV_ENGINE: _reference_request(
                patient_id=reference.patient_id,
                initial_density=_crop(inputs.initial_state.field, roi),
                observed_density=_crop(observed_density, roi),
                brain_mask=_crop(inputs.domain_mask, roi),
                spacing=inputs.observed.spacing,
                calibration_duration=observed_day - start_day,
                forecast_duration=forecast_duration,
                dt_days=min(0.5, experiment.evaluation.dt),
                fraction_days=tuple(fraction_days),
                fraction_doses=tuple(fraction_doses),
                alpha_per_gy=(
                    selected_stage8.candidate.effective_alpha_per_gy
                ),
                alpha_beta_ratio_gy=(
                    selected_stage8.candidate.alpha_beta_ratio_gy
                ),
                optimizer_iterations=optimizer_iterations,
            )
        }

        if reference.patient_id in adc_patient_ids:
            initial_adc = _adc_density(
                patients_root=patients_root,
                inputs=inputs,
                timepoint="t0",
            )
            observed_adc = _adc_density(
                patients_root=patients_root,
                inputs=inputs,
                timepoint="t1",
            )
            requests[ADC_ENGINE] = _reference_request(
                patient_id=reference.patient_id,
                initial_density=_crop(initial_adc, roi),
                observed_density=_crop(observed_adc, roi),
                brain_mask=_crop(inputs.domain_mask, roi),
                spacing=inputs.observed.spacing,
                calibration_duration=observed_day - start_day,
                forecast_duration=forecast_duration,
                dt_days=min(0.5, experiment.evaluation.dt),
                fraction_days=tuple(fraction_days),
                fraction_doses=tuple(fraction_doses),
                alpha_per_gy=(
                    selected_stage8.candidate.effective_alpha_per_gy
                ),
                alpha_beta_ratio_gy=(
                    selected_stage8.candidate.alpha_beta_ratio_gy
                ),
                optimizer_iterations=optimizer_iterations,
            )

        external: dict[str, TumorTwinReferenceResult] = {}
        for engine, request in requests.items():
            signature = reference_request_signature(request)
            work_dir = (
                cache
                / f"patient-{reference.patient_id}"
                / engine
                / signature
            )
            started = time.perf_counter()
            external[engine] = run_external_tumortwin(
                python_executable=tumortwin_python,
                worker_script=worker_script,
                request=request,
                work_dir=work_dir,
            )
            if progress is not None:
                progress(
                    f"[reference-fidelity]   {engine} frozen in "
                    f"{time.perf_counter() - started:.1f}s"
                )

        if progress is not None:
            progress(
                f"[reference-fidelity] patient {reference.patient_id}: "
                "all reference runs frozen; revealing t2"
            )

        target = prepare_stage8_evaluation_target(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=reference.patient_id,
            target_spacing=experiment.evaluation.target_spacing,
            reference=inputs.observed,
        )
        if not np.isclose(
            target.target.days_from_baseline,
            reference.t2_day,
            rtol=0.0,
            atol=1e-6,
        ):
            raise ValueError(
                f"Patient {reference.patient_id}: Stage 9 t2 day mismatch"
            )

        observed_t2 = np.asarray(target.target.gtv.data > 0.5, dtype=bool)
        persistence = np.asarray(
            inputs.observed.gtv.data > 0.5,
            dtype=bool,
        )

        for engine, result in external.items():
            restored = _restore_prediction(
                np.asarray(result.prediction_density, dtype=np.float32),
                full_shape=inputs.domain_mask.shape,
                roi=roi,
            )
            row = _evaluate_row(
                patient_id=reference.patient_id,
                engine=engine,
                result=result,
                prediction_density=restored,
                threshold=observation.enhancing_threshold,
                observed_t2=observed_t2,
                persistence=persistence,
                spacing=target.target.spacing,
                stage9_dice=reference.stage9_dice,
            )
            rows.append(row)
            if progress is not None:
                progress(
                    f"[reference-fidelity]   {engine}: "
                    f"Dice={row.dice:.4f}; "
                    f"delta_vs_persistence={row.delta_vs_persistence:+.4f}; "
                    f"delta_vs_stage9={row.delta_vs_stage9:+.4f}"
                )

    gtv_rows = [row for row in rows if row.engine == GTV_ENGINE]
    adc_rows = [row for row in rows if row.engine == ADC_ENGINE]
    adc_id_set = set(adc_patient_ids)
    paired_gtv_rows = [
        row
        for row in gtv_rows
        if row.patient_id in adc_id_set
    ]

    payload: dict[str, object] = {
        "schema_version": REFERENCE_FIDELITY_SCHEMA_VERSION,
        "kind": "tumortwin_reference_fidelity_diagnostic",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "reference": {
            "name": "TumorTwin",
            "commit_sha": TUMORTWIN_COMMIT,
        },
        "source": {
            "stage8_selection_sha256": (
                selected_stage8.source_manifest_sha256
            ),
            "stage9_selection_sha256": stage9_sha,
            "mpmri_audit_sha256": sha256_file(
                mpmri_audit_path.resolve()
            ),
            "experiment_config_sha256": sha256_file(
                experiment_config_path.resolve()
            ),
            "stage8_protocol_sha256": sha256_file(
                stage8_protocol_path.resolve()
            ),
        },
        "design": {
            "development_only": True,
            "patient_count": len(references),
            "roi_padding_voxels": roi_padding_voxels,
            "gtv_roi_lm_patient_count": len(gtv_rows),
            "adc_t0_t1_patient_count": len(adc_rows),
            "adc_patient_ids": list(adc_patient_ids),
            "adc_uses_t0_t1_only": True,
            "t2_adc_loaded": False,
            "raw_flair_thresholded": False,
            "adc_nonenhancing_roi_used": False,
            "t2_used_only_after_reference_run_freeze": True,
            "enhancing_detection_threshold": (
                observation.enhancing_threshold
            ),
        },
        "summaries": {
            GTV_ENGINE: _summary(gtv_rows),
            ADC_ENGINE: _summary(adc_rows),
            f"{GTV_ENGINE}-adc-paired-subset": _summary(
                paired_gtv_rows
            ),
        },
        "rows": [asdict(row) for row in rows],
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )
    try:
        manifest_path = temporary / "reference_fidelity.json"
        manifest_path.write_text(
            json.dumps(
                payload,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (temporary / "reference_fidelity.sha256").write_text(
            sha256_file(manifest_path)
            + "  reference_fidelity.json\n",
            encoding="ascii",
        )
        _write_csv(temporary / "reference_fidelity.csv", rows)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return payload
