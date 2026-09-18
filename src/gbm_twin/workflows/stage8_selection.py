from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from gbm_twin.calibration.stage8 import Stage8CalibrationConfig
from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.stage8_model_selection import (
    Stage8ModelSelectionResult,
    Stage8PatientCandidateScore,
    select_stage8_model,
)
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_candidate import (
    Stage8PatientCandidateEvaluation,
    evaluate_stage8_candidate,
)
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_model_family import (
    Stage8ModelCandidate,
    build_dose_candidates,
    build_final_alpha_sensitivity_candidates,
    build_memory_candidates,
    build_radiobiology_candidates,
)
from gbm_twin.workflows.stage8_patient import (
    Stage8EvaluationTarget,
    Stage8ForecastInputs,
    prepare_stage8_evaluation_target,
    prepare_stage8_forecast_inputs,
)
from gbm_twin.workflows.stage8_protocol import (
    Stage8ProtocolConfig,
    load_stage8_protocol_config,
)

STAGE8_SELECTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Stage8CandidateFailure:
    patient_id: int
    candidate_id: str
    reason: str


@dataclass(frozen=True)
class Stage8SelectionArtifact:
    directory: Path
    manifest: dict[str, object]


@dataclass(frozen=True)
class _PreparedDevelopmentPatient:
    inputs: Stage8ForecastInputs
    target: Stage8EvaluationTarget


def _audit_development_ids(audit: dict[str, object]) -> tuple[int, ...]:
    raw_patients = audit.get("patients")

    if not isinstance(raw_patients, list):
        raise ValueError("Stage 8 audit patient rows are missing")

    selected: list[int] = []
    for raw in raw_patients:
        if not isinstance(raw, dict):
            raise ValueError("Stage 8 audit patient row must be a mapping")
        if raw.get("split") != "development-exposed":
            continue
        if raw.get("core_eligible") is not True:
            continue

        patient_id = raw.get("patient_id")
        if type(patient_id) is not int:
            raise ValueError("Stage 8 audit patient_id must be an integer")
        selected.append(patient_id)

    result = tuple(sorted(selected))
    if len(result) < 3:
        raise ValueError(
            "Stage 8 model selection needs at least 3 eligible "
            "development-exposed patients"
        )
    return result


def _observation_parameters(
    protocol: Stage8ProtocolConfig,
) -> MRIDetectionObservationParameters:
    return MRIDetectionObservationParameters(
        enhancing_threshold=(
            protocol.observation.enhancing_detection_threshold
        ),
        infiltrative_threshold=(
            protocol.observation.infiltrative_detection_threshold
        ),
        transition_width_mm=(
            protocol.observation.transition_width_mm
        ),
    )


def _calibration_config(
    *,
    protocol: Stage8ProtocolConfig,
    experiment_config_path: Path,
) -> Stage8CalibrationConfig:
    experiment = load_cohort_experiment_config(experiment_config_path)
    evaluation = experiment.evaluation
    return Stage8CalibrationConfig(
        diffusion_values=evaluation.diffusion_values,
        proliferation_values=evaluation.proliferation_values,
        dt_days=evaluation.dt,
        observation_threshold=(
            protocol.observation.enhancing_detection_threshold
        ),
        soft_temperature=0.05,
        volume_weight=evaluation.volume_weight,
        refinement_rounds=evaluation.refinement_rounds,
        upper_boundary_expansion_factor=(
            evaluation.upper_boundary_expansion_factor
        ),
    )


def _candidate_payload(candidate: Stage8ModelCandidate) -> dict[str, object]:
    return asdict(candidate)


def _selection_payload(
    selection: Stage8ModelSelectionResult,
) -> dict[str, object]:
    return {
        "selected_candidate_id": selection.selected_candidate_id,
        "candidate_summaries": [
            asdict(summary)
            for summary in selection.candidate_summaries
        ],
        "loo": {
            "mean_dice": selection.loo_mean_dice,
            "median_dice": selection.loo_median_dice,
            "mean_relative_volume_error": (
                selection.loo_mean_relative_volume_error
            ),
            "selection_counts": selection.loo_selection_counts,
            "folds": [asdict(fold) for fold in selection.loo_folds],
        },
    }


def _write_csv(
    path: Path,
    rows: list[Stage8PatientCandidateEvaluation],
) -> None:
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


def _prepare_patients(
    *,
    patient_ids: tuple[int, ...],
    metadata_root: Path,
    patients_root: Path,
    target_spacing: tuple[float, float, float],
    treatment: CFBTreatmentMetadata,
    observation_parameters: MRIDetectionObservationParameters,
    progress: Callable[[str], None] | None,
) -> dict[int, _PreparedDevelopmentPatient]:
    """Materialize each development patient once for the whole model family."""

    prepared: dict[int, _PreparedDevelopmentPatient] = {}
    total = len(patient_ids)
    for index, patient_id in enumerate(patient_ids, start=1):
        if progress is not None:
            progress(
                f"[stage8] preparing patient {patient_id} "
                f"({index}/{total})"
            )

        started = time.perf_counter()
        inputs = prepare_stage8_forecast_inputs(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=target_spacing,
            treatment=treatment,
            observation_parameters=observation_parameters,
            load_spatial_rtdose=True,
        )
        target = prepare_stage8_evaluation_target(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            target_spacing=target_spacing,
            reference=inputs.observed,
        )
        prepared[patient_id] = _PreparedDevelopmentPatient(
            inputs=inputs,
            target=target,
        )

        if progress is not None:
            progress(
                f"[stage8] prepared patient {patient_id} "
                f"in {time.perf_counter() - started:.1f}s"
            )
    return prepared


def _run_phase(
    *,
    name: str,
    candidates: tuple[Stage8ModelCandidate, ...],
    patient_ids: tuple[int, ...],
    prepared: dict[int, _PreparedDevelopmentPatient],
    observation_parameters: MRIDetectionObservationParameters,
    calibration_config: Stage8CalibrationConfig,
    cache_root: Path,
    workers: int,
    evaluation_cache: dict[
        tuple[int, str],
        Stage8PatientCandidateEvaluation,
    ],
    failures: dict[tuple[int, str], Stage8CandidateFailure],
    progress: Callable[[str], None] | None,
) -> tuple[Stage8ModelSelectionResult, dict[str, object]]:
    candidate_index = {
        candidate.candidate_id: candidate
        for candidate in candidates
    }
    if len(candidate_index) != len(candidates):
        raise ValueError(f"Stage 8 phase {name!r} contains duplicate candidates")

    total_jobs = len(candidates) * len(patient_ids)
    completed_jobs = 0

    if progress is not None:
        progress(
            f"[stage8] phase {name}: {len(candidates)} candidates x "
            f"{len(patient_ids)} patients = {total_jobs} evaluations"
        )

    for candidate in candidates:
        for patient_id in patient_ids:
            completed_jobs += 1
            key = (patient_id, candidate.candidate_id)
            if key in evaluation_cache:
                if progress is not None:
                    progress(
                        f"[stage8] phase {name} {completed_jobs}/{total_jobs}: "
                        f"patient={patient_id} candidate={candidate.candidate_id} "
                        "reused in-memory result"
                    )
                continue
            if key in failures:
                continue

            patient = prepared[patient_id]
            if progress is not None:
                progress(
                    f"[stage8] phase {name} {completed_jobs}/{total_jobs}: "
                    f"patient={patient_id} candidate={candidate.candidate_id} "
                    "starting"
                )

            started = time.perf_counter()

            def calibration_progress(message: str) -> None:
                if progress is not None:
                    progress(
                        f"[stage8]   patient={patient_id} "
                        f"candidate={candidate.candidate_id}: {message}"
                    )

            try:
                row = evaluate_stage8_candidate(
                    inputs=patient.inputs,
                    target=patient.target,
                    candidate=candidate,
                    observation_parameters=observation_parameters,
                    calibration_config=calibration_config,
                    cache_root=cache_root,
                    workers=workers,
                    progress=calibration_progress,
                )
                evaluation_cache[key] = row

                if progress is not None:
                    progress(
                        f"[stage8] phase {name} {completed_jobs}/{total_jobs}: "
                        f"patient={patient_id} candidate={candidate.candidate_id} "
                        f"done in {time.perf_counter() - started:.1f}s; "
                        f"calibration Dice={row.calibration_dice:.4f}; "
                        f"t2 Dice={row.t2_dice:.4f}"
                    )
            except (FileNotFoundError, ValueError) as exc:
                failures[key] = Stage8CandidateFailure(
                    patient_id=patient_id,
                    candidate_id=candidate.candidate_id,
                    reason=str(exc),
                )
                if progress is not None:
                    progress(
                        f"[stage8] phase {name} {completed_jobs}/{total_jobs}: "
                        f"patient={patient_id} candidate={candidate.candidate_id} "
                        f"skipped: {exc}"
                    )

    phase_ids = set(candidate_index)
    scores = tuple(
        Stage8PatientCandidateScore(
            patient_id=row.patient_id,
            candidate_id=row.candidate_id,
            complexity_rank=(
                candidate_index[row.candidate_id].complexity_rank
            ),
            dice=row.t2_dice,
            relative_volume_error=row.t2_relative_volume_error,
            hd95_mm=row.t2_hd95_mm,
            centroid_distance_mm=row.t2_centroid_distance_mm,
        )
        for row in evaluation_cache.values()
        if row.candidate_id in phase_ids
    )
    selection = select_stage8_model(
        scores,
        development_patient_ids=patient_ids,
    )
    selected_candidate = candidate_index[selection.selected_candidate_id]
    payload = {
        "phase": name,
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "selected_candidate": _candidate_payload(selected_candidate),
        **_selection_payload(selection),
    }
    return selection, payload


def select_stage8_model_family(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    protocol_config_path: Path,
    data_audit_root: Path,
    cache_root: Path,
    output_dir: Path,
    workers: int = 1,
    allow_dirty: bool = False,
    progress: Callable[[str], None] | None = None,
) -> Stage8SelectionArtifact:
    destination = output_dir.resolve()
    if destination.exists():
        raise FileExistsError(
            f"Stage 8 model-selection destination already exists: {destination}"
        )
    if workers < 1:
        raise ValueError("workers must be at least 1")

    repository = read_repository_state(repo_root.resolve())
    if repository.dirty and not allow_dirty:
        raise ValueError(
            "Stage 8 model selection requires a clean Git working tree"
        )

    experiment = load_cohort_experiment_config(experiment_config_path)
    protocol = load_stage8_protocol_config(protocol_config_path)
    audit = load_sealed_stage8_data_audit(data_audit_root)

    expected_protocol_sha = audit.manifest.get("protocol_config_sha256")
    actual_protocol_sha = sha256_file(protocol_config_path.resolve())
    if expected_protocol_sha != actual_protocol_sha:
        raise ValueError(
            "Stage 8 audit does not match the current protocol config"
        )

    patient_ids = _audit_development_ids(audit.manifest)
    observation_parameters = _observation_parameters(protocol)
    calibration_config = _calibration_config(
        protocol=protocol,
        experiment_config_path=experiment_config_path,
    )
    metadata_root = (
        experiment.metadata_root
        if experiment.metadata_root.is_absolute()
        else repo_root / experiment.metadata_root
    )
    patients_root = (
        experiment.patients_root
        if experiment.patients_root.is_absolute()
        else repo_root / experiment.patients_root
    )
    treatment = CFBTreatmentMetadata(metadata_root)
    if progress is not None:
        progress(
            f"[stage8] selection start: {len(patient_ids)} "
            "development-exposed patients"
        )

    prepared = _prepare_patients(
        patient_ids=patient_ids,
        metadata_root=metadata_root,
        patients_root=patients_root,
        target_spacing=experiment.evaluation.target_spacing,
        treatment=treatment,
        observation_parameters=observation_parameters,
        progress=progress,
    )

    evaluation_cache: dict[
        tuple[int, str],
        Stage8PatientCandidateEvaluation,
    ] = {}
    failures: dict[tuple[int, str], Stage8CandidateFailure] = {}
    phases: list[dict[str, object]] = []
    all_candidates: dict[str, Stage8ModelCandidate] = {}

    radiobiology_candidates = build_radiobiology_candidates(protocol)
    all_candidates.update(
        (candidate.candidate_id, candidate)
        for candidate in radiobiology_candidates
    )
    radiobiology_selection, phase = _run_phase(
        name="radiobiology",
        candidates=radiobiology_candidates,
        patient_ids=patient_ids,
        prepared=prepared,
        observation_parameters=observation_parameters,
        calibration_config=calibration_config,
        cache_root=cache_root.resolve(),
        workers=workers,
        evaluation_cache=evaluation_cache,
        failures=failures,
        progress=progress,
    )
    phases.append(phase)
    selected_alpha = all_candidates[
        radiobiology_selection.selected_candidate_id
    ].effective_alpha_per_gy

    dose_candidates = build_dose_candidates(
        protocol,
        effective_alpha_per_gy=selected_alpha,
    )
    all_candidates.update(
        (candidate.candidate_id, candidate)
        for candidate in dose_candidates
    )
    dose_selection, phase = _run_phase(
        name="dose",
        candidates=dose_candidates,
        patient_ids=patient_ids,
        prepared=prepared,
        observation_parameters=observation_parameters,
        calibration_config=calibration_config,
        cache_root=cache_root.resolve(),
        workers=workers,
        evaluation_cache=evaluation_cache,
        failures=failures,
        progress=progress,
    )
    phases.append(phase)
    selected_dose = all_candidates[dose_selection.selected_candidate_id]

    memory_candidates = build_memory_candidates(
        protocol,
        effective_alpha_per_gy=selected_alpha,
        use_spatial_rtdose=selected_dose.use_spatial_rtdose,
    )
    all_candidates.update(
        (candidate.candidate_id, candidate)
        for candidate in memory_candidates
    )
    memory_selection, phase = _run_phase(
        name="treatment-memory",
        candidates=memory_candidates,
        patient_ids=patient_ids,
        prepared=prepared,
        observation_parameters=observation_parameters,
        calibration_config=calibration_config,
        cache_root=cache_root.resolve(),
        workers=workers,
        evaluation_cache=evaluation_cache,
        failures=failures,
        progress=progress,
    )
    phases.append(phase)
    selected_memory = all_candidates[memory_selection.selected_candidate_id]

    sensitivity_candidates = build_final_alpha_sensitivity_candidates(
        protocol,
        use_spatial_rtdose=selected_memory.use_spatial_rtdose,
        proliferation_survival=selected_memory.proliferation_survival,
    )
    all_candidates.update(
        (candidate.candidate_id, candidate)
        for candidate in sensitivity_candidates
    )
    final_selection, phase = _run_phase(
        name="final-alpha-sensitivity",
        candidates=sensitivity_candidates,
        patient_ids=patient_ids,
        prepared=prepared,
        observation_parameters=observation_parameters,
        calibration_config=calibration_config,
        cache_root=cache_root.resolve(),
        workers=workers,
        evaluation_cache=evaluation_cache,
        failures=failures,
        progress=progress,
    )
    phases.append(phase)
    selected_candidate = all_candidates[
        final_selection.selected_candidate_id
    ]

    rows = sorted(
        evaluation_cache.values(),
        key=lambda row: (row.candidate_id, row.patient_id),
    )
    failure_rows = sorted(
        failures.values(),
        key=lambda item: (item.candidate_id, item.patient_id),
    )

    payload: dict[str, object] = {
        "schema_version": STAGE8_SELECTION_SCHEMA_VERSION,
        "kind": "stage8_development_model_selection",
        "sealed": True,
        "repository": {
            "commit_sha": repository.commit_sha,
            "dirty": repository.dirty,
        },
        "source": {
            "stage8_data_audit_sha256": sha256_file(
                data_audit_root.resolve() / "stage8_data_audit.json"
            ),
            "protocol_config_sha256": actual_protocol_sha,
            "experiment_config_sha256": sha256_file(
                experiment_config_path.resolve()
            ),
        },
        "leakage_control": {
            "development_t2_loaded": True,
            "development_patient_ids": list(patient_ids),
            "internal_validation_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "candidate_selection_uses_only_development_exposed": True,
        },
        "selection_rule": {
            "design": "sequential_nested_ablation_v1",
            "phase_order": [
                "radiobiology",
                "dose",
                "treatment-memory",
                "final-alpha-sensitivity",
            ],
            "within_phase_ranking": (
                "paired mean Dice desc, median Dice desc, mean relative "
                "volume error asc, complexity asc, candidate ID"
            ),
            "cross_validation": "leave-one-patient-out within each phase",
        },
        "selected_candidate": _candidate_payload(selected_candidate),
        "phases": phases,
        "evaluated_unique_candidate_count": len(
            {row.candidate_id for row in rows}
        ),
        "patient_candidate_results": [asdict(row) for row in rows],
        "failures": [asdict(item) for item in failure_rows],
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=f".{destination.name}-",
        )
    )
    try:
        manifest_path = temporary / "stage8_model_selection.json"
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
        (temporary / "stage8_model_selection.sha256").write_text(
            sha256_file(manifest_path) + "  stage8_model_selection.json\n",
            encoding="ascii",
        )
        _write_csv(temporary / "stage8_model_selection.csv", rows)
        temporary.rename(destination)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise

    return Stage8SelectionArtifact(
        directory=destination,
        manifest=payload,
    )
