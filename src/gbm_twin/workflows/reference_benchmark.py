from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import cast

import numpy as np

from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.observation import (
    MRIDetectionObservationParameters,
    latent_density_from_mri_detection,
)
from gbm_twin.reference.tumortwin import (
    TUMORTWIN_COMMIT,
    TumorTwinReferenceRequest,
    TumorTwinReferenceResult,
    reference_request_signature,
    run_external_tumortwin,
)
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_patient import (
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_protocol import load_stage8_protocol_config
from gbm_twin.workflows.stage8_selection_artifact import (
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage8_validation import (
    preflight_stage8_validation_inputs,
)
from gbm_twin.workflows.stage9_selection_artifact import (
    load_selected_stage9_model,
)

REFERENCE_BENCHMARK_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReferenceBenchmarkRow:
    patient_id: int
    engine: str
    diffusion: float
    proliferation: float
    dice: float
    persistence_dice: float
    delta_vs_persistence: float
    relative_volume_error: float
    hd95_mm: float | None
    centroid_distance_mm: float | None
    stage9_dice: float
    delta_vs_stage9: float


@dataclass(frozen=True)
class ReferenceBenchmarkArtifact:
    directory: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class _Stage9PatientReference:
    patient_id: int
    diffusion: float
    proliferation: float
    stage9_dice: float
    t1_day: float
    t2_day: float


def _mapping(mapping: dict[str, object], key: str) -> dict[str, object]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return cast(dict[str, object], value)


def _list(mapping: dict[str, object], key: str) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return cast(list[object], value)


def _number(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _integer(mapping: dict[str, object], key: str) -> int:
    value = mapping.get(key)
    if type(value) is not int:
        raise ValueError(f"{key} must be integer")
    return cast(int, value)


def _load_stage9_manifest(
    selection_root: Path,
) -> tuple[dict[str, object], str]:
    selected = load_selected_stage9_model(selection_root)
    manifest_path = selection_root.resolve() / "stage9_delayed_selection.json"
    actual_sha = sha256_file(manifest_path)
    if selected.source_manifest_sha256 != actual_sha:
        raise ValueError("Stage 9 selection provenance mismatch")

    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Stage 9 selection must be a JSON object")
    return cast(dict[str, object], raw), actual_sha


def _stage9_patient_references(
    manifest: dict[str, object],
) -> tuple[_Stage9PatientReference, ...]:
    result: list[_Stage9PatientReference] = []

    for raw in _list(manifest, "selected_patient_results"):
        if not isinstance(raw, dict):
            raise ValueError("Stage 9 patient result must be a mapping")
        row = cast(dict[str, object], raw)
        result.append(
            _Stage9PatientReference(
                patient_id=_integer(row, "patient_id"),
                diffusion=_number(row, "diffusion"),
                proliferation=_number(row, "proliferation"),
                stage9_dice=_number(row, "twin_dice"),
                t1_day=_number(row, "t1_day"),
                t2_day=_number(row, "t2_day"),
            )
        )

    if not result:
        raise ValueError("Stage 9 selection has no selected patient results")
    return tuple(sorted(result, key=lambda item: item.patient_id))


def _observation_parameters(
    stage8_protocol_path: Path,
) -> MRIDetectionObservationParameters:
    config = load_stage8_protocol_config(stage8_protocol_path)
    return MRIDetectionObservationParameters(
        enhancing_threshold=(
            config.observation.enhancing_detection_threshold
        ),
        infiltrative_threshold=(
            config.observation.infiltrative_detection_threshold
        ),
        transition_width_mm=config.observation.transition_width_mm,
    )


def _mean_optional(values: list[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return float(fmean(available)) if available else None


def _summary(rows: list[ReferenceBenchmarkRow]) -> dict[str, object]:
    if not rows:
        raise ValueError("Cannot summarize empty reference benchmark")

    deltas = [row.delta_vs_persistence for row in rows]
    return {
        "patient_count": len(rows),
        "mean_dice": float(fmean(row.dice for row in rows)),
        "mean_persistence_dice": float(
            fmean(row.persistence_dice for row in rows)
        ),
        "mean_delta_vs_persistence": float(fmean(deltas)),
        "mean_delta_vs_stage9": float(
            fmean(row.delta_vs_stage9 for row in rows)
        ),
        "mean_relative_volume_error": float(
            fmean(row.relative_volume_error for row in rows)
        ),
        "mean_hd95_mm": _mean_optional([row.hd95_mm for row in rows]),
        "mean_centroid_distance_mm": _mean_optional(
            [row.centroid_distance_mm for row in rows]
        ),
        "better_than_persistence_count": sum(
            value > 1e-6 for value in deltas
        ),
        "equal_to_persistence_count": sum(
            abs(value) <= 1e-6 for value in deltas
        ),
        "worse_than_persistence_count": sum(
            value < -1e-6 for value in deltas
        ),
        "catastrophic_failure_count": sum(value < -0.10 for value in deltas),
    }


def _write_csv(path: Path, rows: list[ReferenceBenchmarkRow]) -> None:
    if not rows:
        return

    fieldnames = list(asdict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def run_reference_benchmark(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    stage8_selection_root: Path,
    stage9_selection_root: Path,
    tumortwin_python: Path,
    worker_script: Path,
    cache_root: Path,
    output_dir: Path,
    run_frozen: bool = True,
    run_calibrated: bool = True,
    optimizer_iterations: int = 8,
    allow_dirty: bool = False,
    progress: Callable[[str], None] | None = None,
) -> ReferenceBenchmarkArtifact:
    if not run_frozen and not run_calibrated:
        raise ValueError("At least one reference benchmark mode is required")

    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Reference benchmark destination exists: {destination}"
        )

    repository = read_repository_state(repo_root.resolve())
    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Reference benchmark requires a clean Git working tree"
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

    patient_references = _stage9_patient_references(stage9_manifest)
    patient_ids = tuple(
        reference.patient_id
        for reference in patient_references
    )
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
            "Reference benchmark preflight failed before execution:\n"
            + preview
        )

    if not tumortwin_python.is_file():
        raise FileNotFoundError(
            f"TumorTwin Python executable not found: {tumortwin_python}"
        )
    if not worker_script.is_file():
        raise FileNotFoundError(
            f"TumorTwin worker script not found: {worker_script}"
        )

    modes: list[str] = []
    if run_frozen:
        modes.append("tumortwin-frozen")
    if run_calibrated:
        modes.append("tumortwin-lm")

    rows: list[ReferenceBenchmarkRow] = []
    cache = cache_root.resolve()
    cache.mkdir(parents=True, exist_ok=True)

    for patient_index, reference in enumerate(patient_references, start=1):
        if progress is not None:
            progress(
                f"[reference] patient {reference.patient_id} "
                f"({patient_index}/{len(patient_references)}): loading t0/t1"
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
        observed_density = latent_density_from_mri_detection(
            inputs.observed.gtv.data > 0.5,
            inputs.domain_mask,
            spacing=inputs.observed.spacing,
            parameters=observation,
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
                f"Patient {reference.patient_id}: Stage 9 t1 day "
                "does not match prepared CFB data"
            )
        calibration_duration = observed_day - start_day

        shifted_fraction_days: list[float] = []
        fraction_doses: list[float] = []
        for day in inputs.schedule.fraction_days:
            shifted_day = day - start_day
            if shifted_day >= 0.0:
                shifted_fraction_days.append(shifted_day)
                fraction_doses.append(inputs.schedule.dose_per_fraction_gy)

        forecast_duration = reference.t2_day - reference.t1_day
        if forecast_duration <= 0.0:
            raise ValueError(
                f"Patient {reference.patient_id}: invalid Stage 9 t1/t2 days"
            )

        mode_results: dict[str, TumorTwinReferenceRequest] = {}
        for mode in modes:
            request = TumorTwinReferenceRequest(
                patient_id=reference.patient_id,
                initial_density=inputs.initial_state.field,
                observed_density=observed_density,
                brain_mask=inputs.domain_mask,
                spacing_mm=inputs.observed.spacing,
                calibration_duration_days=calibration_duration,
                forecast_duration_days=forecast_duration,
                dt_days=min(0.5, experiment.evaluation.dt),
                radiotherapy_fraction_days=tuple(shifted_fraction_days),
                radiotherapy_fraction_doses_gy=tuple(fraction_doses),
                alpha_per_gy=(
                    selected_stage8.candidate.effective_alpha_per_gy
                ),
                alpha_beta_ratio_gy=(
                    selected_stage8.candidate.alpha_beta_ratio_gy
                ),
                mode="frozen" if mode == "tumortwin-frozen" else "calibrate",
                frozen_diffusion=reference.diffusion,
                frozen_proliferation=reference.proliferation,
                diffusion_bounds=(0.0, 2.0),
                proliferation_bounds=(0.0, 0.5),
                optimizer_iterations=optimizer_iterations,
            )
            mode_results[mode] = request

        external_results: dict[str, TumorTwinReferenceResult] = {}
        for mode in modes:
            request = mode_results[mode]
            signature = reference_request_signature(request)
            work_dir = (
                cache
                / f"patient-{reference.patient_id}"
                / mode
                / signature
            )
            started = time.perf_counter()
            external_results[mode] = run_external_tumortwin(
                python_executable=tumortwin_python,
                worker_script=worker_script,
                request=request,
                work_dir=work_dir,
            )
            if progress is not None:
                progress(
                    f"[reference]   {mode} pre-t2 run frozen in "
                    f"{time.perf_counter() - started:.1f}s"
                )

        if progress is not None:
            progress(
                f"[reference] patient {reference.patient_id}: "
                "reference runs frozen; revealing t2 for evaluation"
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
                f"Patient {reference.patient_id}: Stage 9 t2 day "
                "does not match prepared CFB target"
            )
        observed_t2 = np.asarray(target.target.gtv.data > 0.5, dtype=bool)
        persistence = np.asarray(inputs.observed.gtv.data > 0.5, dtype=bool)
        persistence_dice = dice_score(persistence, observed_t2)

        for mode in modes:
            result = external_results[mode]
            evaluation_started = time.perf_counter()
            prediction_density = np.asarray(
                result.prediction_density,
                dtype=np.float32,
            )
            predicted = np.asarray(
                prediction_density >= observation.enhancing_threshold,
                dtype=bool,
            )
            score = dice_score(predicted, observed_t2)
            row = ReferenceBenchmarkRow(
                patient_id=reference.patient_id,
                engine=mode,
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
                    spacing=target.target.spacing,
                ),
                centroid_distance_mm=centroid_distance_mm(
                    predicted,
                    observed_t2,
                    spacing=target.target.spacing,
                ),
                stage9_dice=reference.stage9_dice,
                delta_vs_stage9=score - reference.stage9_dice,
            )
            rows.append(row)

            if progress is not None:
                progress(
                    f"[reference]   {mode} evaluated in "
                    f"{time.perf_counter() - evaluation_started:.1f}s; "
                    f"Dice={score:.4f}; "
                    f"delta_vs_persistence={row.delta_vs_persistence:+.4f}; "
                    f"delta_vs_stage9={row.delta_vs_stage9:+.4f}"
                )

    summaries = {
        mode: _summary([row for row in rows if row.engine == mode])
        for mode in modes
    }
    payload: dict[str, object] = {
        "schema_version": REFERENCE_BENCHMARK_SCHEMA_VERSION,
        "kind": "published_reference_model_benchmark",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "reference": {
            "name": "TumorTwin",
            "repository": (
                "https://github.com/OncologyModelingGroup/TumorTwin"
            ),
            "commit_sha": TUMORTWIN_COMMIT,
            "license_note": (
                "External package is not vendored; it is installed into an "
                "isolated local environment under its upstream research license."
            ),
        },
        "source": {
            "stage8_selection_sha256": (
                selected_stage8.source_manifest_sha256
            ),
            "stage9_selection_sha256": stage9_sha,
            "experiment_config_sha256": sha256_file(
                experiment_config_path.resolve()
            ),
            "stage8_protocol_sha256": sha256_file(
                stage8_protocol_path.resolve()
            ),
        },
        "design": {
            "development_only": True,
            "patient_count": len(patient_references),
            "modes": modes,
            "same_observation_model": True,
            "same_t2_metrics": True,
            "frozen_mode_uses_stage8_d_rho": True,
            "calibrated_mode_uses_t0_t1_only": True,
            "t2_used_only_for_evaluation": True,
            "adc_cellularity_used": False,
        },
        "summaries": summaries,
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
        manifest_path = temporary / "reference_benchmark.json"
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
        (temporary / "reference_benchmark.sha256").write_text(
            sha256_file(manifest_path)
            + "  reference_benchmark.json\n",
            encoding="ascii",
        )
        _write_csv(temporary / "reference_benchmark.csv", rows)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return ReferenceBenchmarkArtifact(
        directory=destination,
        manifest=payload,
    )
