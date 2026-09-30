from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean, median
from typing import cast

from gbm_twin.data.cfb_treatment import CFBTreatmentMetadata
from gbm_twin.evaluation.config import load_cohort_experiment_config
from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.models.delayed_response import DelayedResponseParameters
from gbm_twin.models.observation import MRIDetectionObservationParameters
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.workflows.provenance import sha256_file
from gbm_twin.workflows.repository import read_repository_state
from gbm_twin.workflows.stage8_data_audit import (
    load_sealed_stage8_data_audit,
)
from gbm_twin.workflows.stage8_selection_artifact import (
    SelectedStage8Model,
    load_selected_stage8_model,
)
from gbm_twin.workflows.stage8_validation import (
    preflight_stage8_validation_inputs,
)
from gbm_twin.workflows.stage9_forecast import simulate_stage9_forecast
from gbm_twin.workflows.stage9_selection import (
    FrozenStage8Kinetics,
    _development_and_reserve_ids,
    _mask_volume_cm3,
    _observation_parameters,
    _optional_mean,
    _prepare_patients,
    _PreparedPatient,
    _stage8_frozen_kinetics,
    _trajectory_group,
)
from gbm_twin.workflows.stage9_selection_artifact import (
    SelectedStage9Model,
    load_selected_stage9_model,
)
from gbm_twin.workflows.stage10_forecast import simulate_stage10_forecast
from gbm_twin.workflows.stage10_model_family import (
    Stage10Candidate,
    build_stage10_candidates,
)
from gbm_twin.workflows.stage10_protocol import (
    Stage10ProtocolConfig,
    load_stage10_protocol_config,
)

STAGE10_SELECTION_SCHEMA_VERSION = 1
STAGE10_SELECTION_KIND = (
    "stage10_decoupled_damage_development_selection"
)


@dataclass(frozen=True)
class Stage10PatientCandidateEvaluation:
    patient_id: int
    candidate_id: str
    candidate_kind: str
    damage_half_life_days: float
    complexity_rank: int
    diffusion: float
    proliferation: float
    twin_dice: float
    persistence_dice: float
    delta_vs_persistence: float
    relative_volume_error: float
    persistence_relative_volume_error: float
    hd95_mm: float | None
    persistence_hd95_mm: float | None
    centroid_distance_mm: float | None
    persistence_centroid_distance_mm: float | None
    t1_day: float
    t2_day: float
    forecast_horizon_days: float
    observed_t1_volume_cm3: float
    observed_t2_volume_cm3: float
    predicted_t2_volume_cm3: float
    observed_volume_change_fraction: float
    trajectory_group: str


@dataclass(frozen=True)
class Stage10CandidateSummary:
    candidate_id: str
    candidate_kind: str
    damage_half_life_days: float
    complexity_rank: int
    patient_count: int
    mean_dice: float
    median_dice: float
    mean_delta_vs_persistence: float
    median_delta_vs_persistence: float
    mean_relative_volume_error: float
    mean_hd95_mm: float | None
    catastrophic_failure_count: int
    better_count: int
    equal_count: int
    worse_count: int
    regression_patient_count: int
    regression_mean_delta_vs_persistence: float | None
    growth_patient_count: int
    growth_mean_delta_vs_persistence: float | None
    stable_patient_count: int
    stable_mean_delta_vs_persistence: float | None


@dataclass(frozen=True)
class Stage10SelectionArtifact:
    directory: Path
    manifest: dict[str, object]


def _mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        dict,
    ):
        raise ValueError(
            f"{key} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _list(
    mapping: dict[str, object],
    key: str,
) -> list[object]:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        list,
    ):
        raise ValueError(
            f"{key} must be a list"
        )

    return cast(
        list[object],
        value,
    )


def _int(
    value: object,
    *,
    name: str,
) -> int:
    if type(value) is not int:
        raise ValueError(
            f"{name} must be an integer"
        )

    return cast(
        int,
        value,
    )


def _float(
    value: object,
    *,
    name: str,
) -> float:
    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"{name} must be numeric"
        )

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):
        raise ValueError(
            f"{name} must be finite"
        )

    return result


def _load_sealed_json(
    root: Path,
    *,
    basename: str,
) -> tuple[
    dict[str, object],
    str,
]:
    directory = root.resolve()

    manifest_path = (
        directory
        / f"{basename}.json"
    )

    seal_path = (
        directory
        / f"{basename}.sha256"
    )

    if (
        not manifest_path.is_file()
        or not seal_path.is_file()
    ):
        raise FileNotFoundError(
            f"Incomplete sealed artifact: {directory}"
        )

    tokens = seal_path.read_text(
        encoding="ascii"
    ).split()

    actual = sha256_file(
        manifest_path
    )

    if (
        not tokens
        or tokens[0] != actual
    ):
        raise ValueError(
            f"Checksum mismatch for {manifest_path}"
        )

    raw: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            f"{manifest_path} must contain a JSON object"
        )

    return (
        cast(
            dict[str, object],
            raw,
        ),
        actual,
    )


def _reference_fidelity_gate(
    root: Path,
    *,
    expected_stage9_sha256: str,
) -> str:
    manifest, actual_sha = (
        _load_sealed_json(
            root,
            basename=(
                "reference_fidelity"
            ),
        )
    )

    if manifest.get(
        "sealed"
    ) is not True:
        raise ValueError(
            "Reference Fidelity v2 is not sealed"
        )

    if (
        manifest.get(
            "kind"
        )
        != "tumortwin_reference_fidelity_diagnostic"
    ):
        raise ValueError(
            "Artifact is not Reference Fidelity v2"
        )

    source = _mapping(
        manifest,
        "source",
    )

    if (
        source.get(
            "stage9_selection_sha256"
        )
        != expected_stage9_sha256
    ):
        raise ValueError(
            "Reference Fidelity v2 does not reference the selected "
            "Stage 9 artifact"
        )

    design = _mapping(
        manifest,
        "design",
    )

    required_flags = {
        "development_only": True,
        "adc_uses_t0_t1_only": True,
        "t2_adc_loaded": False,
        "raw_flair_thresholded": False,
        "t2_used_only_after_reference_run_freeze": True,
    }

    for key, expected in (
        required_flags.items()
    ):
        if design.get(
            key
        ) is not expected:
            raise ValueError(
                "Reference Fidelity v2 leakage contract is inconsistent: "
                f"{key}"
            )

    return actual_sha


def _stage9_expected_dice(
    stage9_root: Path,
    *,
    expected_sha256: str,
) -> dict[
    int,
    float,
]:
    manifest, actual_sha = (
        _load_sealed_json(
            stage9_root,
            basename=(
                "stage9_delayed_selection"
            ),
        )
    )

    if actual_sha != expected_sha256:
        raise ValueError(
            "Stage 9 manifest does not match loaded selected model"
        )

    expected: dict[
        int,
        float,
    ] = {}

    for raw in _list(
        manifest,
        "selected_patient_results",
    ):
        if not isinstance(
            raw,
            dict,
        ):
            raise ValueError(
                "Stage 9 selected patient row must be a mapping"
            )

        row = cast(
            dict[str, object],
            raw,
        )

        patient_id = _int(
            row.get(
                "patient_id"
            ),
            name="patient_id",
        )

        expected[
            patient_id
        ] = _float(
            row.get(
                "twin_dice"
            ),
            name="twin_dice",
        )

    if not expected:
        raise ValueError(
            "Stage 9 selected patient results are empty"
        )

    return expected


def _evaluate_candidate(
    *,
    candidate: Stage10Candidate,
    selected_stage9: SelectedStage9Model,
    patient_id: int,
    patient: _PreparedPatient,
    kinetics: FrozenStage8Kinetics,
    selected_stage8: SelectedStage8Model,
    observation: MRIDetectionObservationParameters,
    dt_days: float,
) -> Stage10PatientCandidateEvaluation:
    radiobiology = (
        RadiobiologyParameters(
            alpha_per_gy=(
                selected_stage8
                .candidate
                .effective_alpha_per_gy
            ),
            alpha_beta_ratio_gy=(
                selected_stage8
                .candidate
                .alpha_beta_ratio_gy
            ),
        )
    )

    growth = (
        ReactionDiffusionParameters(
            diffusion=(
                kinetics.diffusion
            ),
            proliferation=(
                kinetics.proliferation
            ),
        )
    )

    if (
        candidate.kind
        == "stage9-control"
    ):
        forecast = (
            simulate_stage9_forecast(
                inputs=patient.inputs,
                target_day=(
                    patient
                    .target
                    .target
                    .days_from_baseline
                ),
                growth=growth,
                radiobiology=(
                    radiobiology
                ),
                proliferation_survival=(
                    selected_stage8
                    .candidate
                    .proliferation_survival
                ),
                delayed=(
                    DelayedResponseParameters(
                        damage_transfer_fraction=(
                            selected_stage9
                            .candidate
                            .damage_transfer_fraction
                        ),
                        damage_half_life_days=(
                            selected_stage9
                            .candidate
                            .damage_half_life_days
                        ),
                        damaged_visibility=(
                            selected_stage9
                            .candidate
                            .damaged_visibility
                        ),
                    )
                ),
                dt_days=dt_days,
                observation_parameters=(
                    observation
                ),
            )
        )

    else:
        forecast = (
            simulate_stage10_forecast(
                inputs=patient.inputs,
                target_day=(
                    patient
                    .target
                    .target
                    .days_from_baseline
                ),
                growth=growth,
                radiobiology=(
                    radiobiology
                ),
                proliferation_survival=(
                    selected_stage8
                    .candidate
                    .proliferation_survival
                ),
                damage_half_life_days=(
                    candidate
                    .damage_half_life_days
                ),
                dt_days=dt_days,
                observation_parameters=(
                    observation
                ),
            )
        )

    predicted = (
        forecast.prediction_mask
    )

    twin_dice = dice_score(
        predicted,
        patient.observed_t2,
    )

    spacing = (
        patient
        .target
        .target
        .spacing
    )

    t1_volume = (
        _mask_volume_cm3(
            patient.persistence,
            spacing=spacing,
        )
    )

    t2_volume = (
        _mask_volume_cm3(
            patient.observed_t2,
            spacing=spacing,
        )
    )

    predicted_volume = (
        _mask_volume_cm3(
            predicted,
            spacing=spacing,
        )
    )

    volume_change = (
        0.0
        if t1_volume <= 0.0
        else (
            t2_volume
            - t1_volume
        )
        / t1_volume
    )

    return (
        Stage10PatientCandidateEvaluation(
            patient_id=patient_id,
            candidate_id=(
                candidate.candidate_id
            ),
            candidate_kind=(
                candidate.kind
            ),
            damage_half_life_days=(
                candidate
                .damage_half_life_days
            ),
            complexity_rank=(
                candidate
                .complexity_rank
            ),
            diffusion=(
                kinetics.diffusion
            ),
            proliferation=(
                kinetics.proliferation
            ),
            twin_dice=twin_dice,
            persistence_dice=(
                patient.persistence_dice
            ),
            delta_vs_persistence=(
                twin_dice
                - patient
                .persistence_dice
            ),
            relative_volume_error=(
                relative_volume_error(
                    predicted,
                    patient.observed_t2,
                )
            ),
            persistence_relative_volume_error=(
                patient
                .persistence_relative_volume_error
            ),
            hd95_mm=(
                hausdorff95_mm(
                    predicted,
                    patient.observed_t2,
                    spacing=spacing,
                )
            ),
            persistence_hd95_mm=(
                patient
                .persistence_hd95_mm
            ),
            centroid_distance_mm=(
                centroid_distance_mm(
                    predicted,
                    patient.observed_t2,
                    spacing=spacing,
                )
            ),
            persistence_centroid_distance_mm=(
                patient
                .persistence_centroid_distance_mm
            ),
            t1_day=(
                patient
                .inputs
                .observed
                .days_from_baseline
            ),
            t2_day=(
                patient
                .target
                .target
                .days_from_baseline
            ),
            forecast_horizon_days=(
                patient
                .target
                .target
                .days_from_baseline
                - patient
                .inputs
                .observed
                .days_from_baseline
            ),
            observed_t1_volume_cm3=(
                t1_volume
            ),
            observed_t2_volume_cm3=(
                t2_volume
            ),
            predicted_t2_volume_cm3=(
                predicted_volume
            ),
            observed_volume_change_fraction=(
                volume_change
            ),
            trajectory_group=(
                _trajectory_group(
                    volume_change
                )
            ),
        )
    )


def _subgroup_mean(
    rows: list[
        Stage10PatientCandidateEvaluation
    ],
    group: str,
) -> tuple[
    int,
    float | None,
]:
    values = [
        row.delta_vs_persistence
        for row in rows
        if row.trajectory_group
        == group
    ]

    return (
        len(
            values
        ),
        (
            None
            if not values
            else float(
                fmean(
                    values
                )
            )
        ),
    )


def _summary(
    rows: list[
        Stage10PatientCandidateEvaluation
    ],
    *,
    catastrophic_threshold: float,
) -> Stage10CandidateSummary:
    if not rows:
        raise ValueError(
            "Cannot summarize empty Stage 10 candidate rows"
        )

    candidate_ids = {
        row.candidate_id
        for row in rows
    }

    if len(
        candidate_ids
    ) != 1:
        raise ValueError(
            "Stage 10 summary rows mix candidates"
        )

    kinds = {
        row.candidate_kind
        for row in rows
    }

    half_lives = {
        row.damage_half_life_days
        for row in rows
    }

    ranks = {
        row.complexity_rank
        for row in rows
    }

    if (
        len(
            kinds
        )
        != 1
        or len(
            half_lives
        )
        != 1
        or len(
            ranks
        )
        != 1
    ):
        raise ValueError(
            "Stage 10 candidate metadata is inconsistent"
        )

    deltas = [
        row.delta_vs_persistence
        for row in rows
    ]

    (
        regression_count,
        regression_mean,
    ) = _subgroup_mean(
        rows,
        "regression",
    )

    (
        growth_count,
        growth_mean,
    ) = _subgroup_mean(
        rows,
        "growth",
    )

    (
        stable_count,
        stable_mean,
    ) = _subgroup_mean(
        rows,
        "stable",
    )

    return Stage10CandidateSummary(
        candidate_id=(
            rows[0].candidate_id
        ),
        candidate_kind=(
            kinds.pop()
        ),
        damage_half_life_days=(
            half_lives.pop()
        ),
        complexity_rank=(
            ranks.pop()
        ),
        patient_count=len(
            rows
        ),
        mean_dice=float(
            fmean(
                row.twin_dice
                for row in rows
            )
        ),
        median_dice=float(
            median(
                row.twin_dice
                for row in rows
            )
        ),
        mean_delta_vs_persistence=(
            float(
                fmean(
                    deltas
                )
            )
        ),
        median_delta_vs_persistence=(
            float(
                median(
                    deltas
                )
            )
        ),
        mean_relative_volume_error=(
            float(
                fmean(
                    row
                    .relative_volume_error
                    for row in rows
                )
            )
        ),
        mean_hd95_mm=(
            _optional_mean(
                [
                    row.hd95_mm
                    for row in rows
                ]
            )
        ),
        catastrophic_failure_count=(
            sum(
                value
                < catastrophic_threshold
                for value in deltas
            )
        ),
        better_count=sum(
            value > 1e-6
            for value in deltas
        ),
        equal_count=sum(
            abs(
                value
            )
            <= 1e-6
            for value in deltas
        ),
        worse_count=sum(
            value < -1e-6
            for value in deltas
        ),
        regression_patient_count=(
            regression_count
        ),
        regression_mean_delta_vs_persistence=(
            regression_mean
        ),
        growth_patient_count=(
            growth_count
        ),
        growth_mean_delta_vs_persistence=(
            growth_mean
        ),
        stable_patient_count=(
            stable_count
        ),
        stable_mean_delta_vs_persistence=(
            stable_mean
        ),
    )


def select_stage10_summary(
    summaries: tuple[
        Stage10CandidateSummary,
        ...,
    ],
    *,
    control: Stage10CandidateSummary,
    config: Stage10ProtocolConfig,
) -> Stage10CandidateSummary:
    if (
        control
        .regression_mean_delta_vs_persistence
        is None
        or control
        .growth_mean_delta_vs_persistence
        is None
    ):
        raise ValueError(
            "Stage 10 control lacks required trajectory subgroups"
        )

    eligible: list[
        Stage10CandidateSummary
    ] = []

    for summary in summaries:
        if (
            summary.candidate_id
            == control.candidate_id
        ):
            continue

        if (
            summary.candidate_kind
            != "decoupled"
        ):
            continue

        if (
            summary
            .regression_mean_delta_vs_persistence
            is None
            or summary
            .growth_mean_delta_vs_persistence
            is None
        ):
            continue

        if (
            summary
            .catastrophic_failure_count
            >= control
            .catastrophic_failure_count
        ):
            continue

        regression_gain = (
            summary
            .regression_mean_delta_vs_persistence
            - control
            .regression_mean_delta_vs_persistence
        )

        if (
            regression_gain
            <= config
            .selection
            .min_regression_delta_gain
        ):
            continue

        if (
            summary
            .growth_mean_delta_vs_persistence
            < control
            .growth_mean_delta_vs_persistence
            - config
            .selection
            .max_growth_delta_degradation
        ):
            continue

        if (
            summary.mean_dice
            < control.mean_dice
            - config
            .selection
            .max_mean_dice_degradation
        ):
            continue

        eligible.append(
            summary
        )

    if not eligible:
        return control

    return min(
        eligible,
        key=lambda item: (
            item
            .catastrophic_failure_count,
            -cast(
                float,
                item
                .regression_mean_delta_vs_persistence,
            ),
            -item.mean_dice,
            item
            .mean_relative_volume_error,
            (
                float(
                    "inf"
                )
                if item.mean_hd95_mm
                is None
                else item.mean_hd95_mm
            ),
            item.complexity_rank,
            item.candidate_id,
        ),
    )


def _write_csv(
    path: Path,
    rows: list[
        Stage10PatientCandidateEvaluation
    ],
) -> None:
    if not rows:
        return

    fieldnames = list(
        asdict(
            rows[0]
        ).keys()
    )

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
            lineterminator="\n",
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                asdict(
                    row
                )
            )


def select_stage10_decoupled_damage(
    *,
    repo_root: Path,
    experiment_config_path: Path,
    stage8_protocol_path: Path,
    stage10_protocol_path: Path,
    data_audit_root: Path,
    stage8_selection_root: Path,
    stage8_validation_root: Path,
    stage9_selection_root: Path,
    reference_fidelity_root: Path,
    output_dir: Path,
    allow_dirty: bool = False,
    progress: Callable[
        [str],
        None,
    ]
    | None = None,
) -> Stage10SelectionArtifact:
    destination = (
        output_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            "Stage 10 selection destination already exists: "
            f"{destination}"
        )

    repository = (
        read_repository_state(
            repo_root.resolve()
        )
    )

    if (
        repository.dirty
        and not allow_dirty
    ):
        raise ValueError(
            "Stage 10 selection requires a clean Git working tree"
        )

    stage10 = (
        load_stage10_protocol_config(
            stage10_protocol_path
        )
    )

    selected_stage8 = (
        load_selected_stage8_model(
            stage8_selection_root
        )
    )

    selected_stage9 = (
        load_selected_stage9_model(
            stage9_selection_root
        )
    )

    stage9_candidate = (
        selected_stage9.candidate
    )

    if (
        not math.isclose(
            stage9_candidate
            .damage_transfer_fraction,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            stage9_candidate
            .damaged_visibility,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            stage9_candidate
            .damage_half_life_days,
            120.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
    ):
        raise ValueError(
            "Stage 10 protocol requires the sealed Stage 9 v2 "
            "transfer=1, visibility=1, half-life=120d control"
        )

    audit = (
        load_sealed_stage8_data_audit(
            data_audit_root
        )
    )

    audit_sha = sha256_file(
        data_audit_root.resolve()
        / "stage8_data_audit.json"
    )

    if (
        selected_stage8
        .stage8_data_audit_sha256
        != audit_sha
        or selected_stage9
        .stage8_data_audit_sha256
        != audit_sha
    ):
        raise ValueError(
            "Stage 8/9 selections do not match the sealed data audit"
        )

    experiment_sha = (
        sha256_file(
            experiment_config_path.resolve()
        )
    )

    stage8_protocol_sha = (
        sha256_file(
            stage8_protocol_path.resolve()
        )
    )

    if (
        selected_stage8
        .experiment_config_sha256
        != experiment_sha
        or selected_stage9
        .experiment_config_sha256
        != experiment_sha
    ):
        raise ValueError(
            "Stage 8/9 selections do not match experiment config"
        )

    if (
        selected_stage8
        .protocol_config_sha256
        != stage8_protocol_sha
        or selected_stage9
        .stage8_protocol_sha256
        != stage8_protocol_sha
    ):
        raise ValueError(
            "Stage 8/9 selections do not match Stage 8 protocol"
        )

    (
        kinetics,
        _stage8_selection_manifest,
        _stage8_validation_manifest,
        stage8_selection_sha,
        stage8_validation_sha,
    ) = _stage8_frozen_kinetics(
        stage8_selection_root=(
            stage8_selection_root
        ),
        stage8_validation_root=(
            stage8_validation_root
        ),
        selected=selected_stage8,
    )

    if (
        selected_stage9
        .stage8_model_selection_sha256
        != stage8_selection_sha
        or selected_stage9
        .stage8_internal_validation_sha256
        != stage8_validation_sha
    ):
        raise ValueError(
            "Stage 9 does not reference the sealed Stage 8 artifacts"
        )

    reference_fidelity_sha = (
        _reference_fidelity_gate(
            reference_fidelity_root,
            expected_stage9_sha256=(
                selected_stage9
                .source_manifest_sha256
            ),
        )
    )

    (
        development_ids,
        reserve_ids,
        holdout_ids,
    ) = _development_and_reserve_ids(
        audit.manifest,
        development_ids=set(
            kinetics
        ),
    )

    if (
        reserve_ids
        != selected_stage9
        .reserve_patient_ids
        or holdout_ids
        != selected_stage9
        .untouched_holdout_patient_ids
    ):
        raise ValueError(
            "Stage 10 split no longer matches the sealed Stage 9 split"
        )

    expected_stage9 = (
        _stage9_expected_dice(
            stage9_selection_root,
            expected_sha256=(
                selected_stage9
                .source_manifest_sha256
            ),
        )
    )

    if (
        set(
            expected_stage9
        )
        != set(
            development_ids
        )
    ):
        raise ValueError(
            "Stage 9 selected patient results do not match "
            "the Stage 10 development cohort"
        )

    experiment = (
        load_cohort_experiment_config(
            experiment_config_path
        )
    )

    metadata_root = (
        experiment.metadata_root
        if experiment
        .metadata_root
        .is_absolute()
        else (
            repo_root.resolve()
            / experiment.metadata_root
        )
    )

    patients_root = (
        experiment.patients_root
        if experiment
        .patients_root
        .is_absolute()
        else (
            repo_root.resolve()
            / experiment.patients_root
        )
    )

    issues = (
        preflight_stage8_validation_inputs(
            patients_root=patients_root,
            patient_ids=(
                development_ids
            ),
            require_spatial_rtdose=(
                selected_stage8
                .candidate
                .use_spatial_rtdose
            ),
        )
    )

    if issues:
        preview = "\n".join(
            (
                f"  patient {item.patient_id}: "
                f"{item.input_name} -> "
                f"{item.expected_path}"
            )
            for item in issues[
                :30
            ]
        )

        raise FileNotFoundError(
            "Stage 10 development inputs are incomplete:\n"
            + preview
        )

    observation = (
        _observation_parameters(
            stage8_protocol_path
        )
    )

    treatment = (
        CFBTreatmentMetadata(
            metadata_root
        )
    )

    prepared = _prepare_patients(
        patient_ids=development_ids,
        metadata_root=metadata_root,
        patients_root=patients_root,
        target_spacing=(
            experiment
            .evaluation
            .target_spacing
        ),
        treatment=treatment,
        observation=observation,
        load_spatial_rtdose=(
            selected_stage8
            .candidate
            .use_spatial_rtdose
        ),
        progress=progress,
    )

    candidates = (
        build_stage10_candidates(
            selected_stage9=(
                stage9_candidate
            ),
            half_life_days=(
                stage10
                .visible_damage_half_life_days
            ),
        )
    )

    rows: list[
        Stage10PatientCandidateEvaluation
    ] = []

    total = (
        len(
            candidates
        )
        * len(
            development_ids
        )
    )

    job = 0

    for candidate in candidates:
        for patient_id in (
            development_ids
        ):
            job += 1
            started = (
                time.perf_counter()
            )

            if progress is not None:
                progress(
                    f"[stage10] {job}/{total}: "
                    f"patient={patient_id} "
                    f"candidate={candidate.candidate_id}"
                )

            row = _evaluate_candidate(
                candidate=candidate,
                selected_stage9=(
                    selected_stage9
                ),
                patient_id=(
                    patient_id
                ),
                patient=(
                    prepared[
                        patient_id
                    ]
                ),
                kinetics=(
                    kinetics[
                        patient_id
                    ]
                ),
                selected_stage8=(
                    selected_stage8
                ),
                observation=(
                    observation
                ),
                dt_days=(
                    experiment
                    .evaluation
                    .dt
                ),
            )

            if (
                candidate.kind
                == "stage9-control"
                and not math.isclose(
                    row.twin_dice,
                    expected_stage9[
                        patient_id
                    ],
                    rel_tol=0.0,
                    abs_tol=1e-6,
                )
            ):
                raise RuntimeError(
                    "Stage 10 control does not reproduce sealed Stage 9 "
                    f"for patient {patient_id}: "
                    f"{row.twin_dice:.8f} vs "
                    f"{expected_stage9[patient_id]:.8f}"
                )

            rows.append(
                row
            )

            if progress is not None:
                progress(
                    "[stage10]   done in "
                    f"{time.perf_counter() - started:.1f}s; "
                    f"Dice={row.twin_dice:.4f}; "
                    f"delta={row.delta_vs_persistence:+.4f}"
                )

    summaries = tuple(
        _summary(
            [
                row
                for row in rows
                if row.candidate_id
                == candidate.candidate_id
            ],
            catastrophic_threshold=(
                stage10
                .selection
                .catastrophic_delta_vs_persistence
            ),
        )
        for candidate in candidates
    )

    control = next(
        summary
        for summary in summaries
        if summary.candidate_kind
        == "stage9-control"
    )

    selected = (
        select_stage10_summary(
            summaries,
            control=control,
            config=stage10,
        )
    )

    decision = (
        "decoupled_candidate_advanced"
        if selected.candidate_kind
        == "decoupled"
        else (
            "no_decoupled_candidate_advanced"
        )
    )

    selected_rows = [
        row
        for row in rows
        if row.candidate_id
        == selected.candidate_id
    ]

    payload: dict[
        str,
        object,
    ] = {
        "schema_version": (
            STAGE10_SELECTION_SCHEMA_VERSION
        ),
        "kind": (
            STAGE10_SELECTION_KIND
        ),
        "sealed": True,
        "repository": {
            "commit_sha": (
                repository.commit_sha
            ),
            "dirty": (
                repository.dirty
            ),
        },
        "source": {
            "stage8_data_audit_sha256": (
                audit_sha
            ),
            "stage8_model_selection_sha256": (
                stage8_selection_sha
            ),
            "stage8_internal_validation_sha256": (
                stage8_validation_sha
            ),
            "stage9_selection_sha256": (
                selected_stage9
                .source_manifest_sha256
            ),
            "reference_fidelity_v2_sha256": (
                reference_fidelity_sha
            ),
            "stage8_protocol_sha256": (
                stage8_protocol_sha
            ),
            "stage10_protocol_sha256": (
                sha256_file(
                    stage10_protocol_path.resolve()
                )
            ),
            "experiment_config_sha256": (
                experiment_sha
            ),
        },
        "leakage_control": {
            "development_patient_ids": (
                list(
                    development_ids
                )
            ),
            "reserve_patient_ids": (
                list(
                    reserve_ids
                )
            ),
            "untouched_holdout_patient_ids": (
                list(
                    holdout_ids
                )
            ),
            "development_only": True,
            "reserve_t2_loaded": False,
            "untouched_holdout_t2_loaded": False,
            "patient_specific_kinetics_refit": False,
        },
        "base_stage9_candidate": {
            "candidate_id": (
                stage9_candidate
                .candidate_id
            ),
            "damage_transfer_fraction": (
                stage9_candidate
                .damage_transfer_fraction
            ),
            "damage_half_life_days": (
                stage9_candidate
                .damage_half_life_days
            ),
            "damaged_visibility": (
                stage9_candidate
                .damaged_visibility
            ),
        },
        "design": {
            "name": (
                stage10.design
            ),
            "frozen_patient_specific_parameters": [
                "D",
                "rho",
            ],
            "frozen_global_parameters": [
                "radiobiology",
                "stage8_proliferation_survival",
                "damage_transfer_fraction=1",
                "damaged_visibility=1",
                "inert_retention_fraction=1",
            ],
            "candidate_visible_damage_half_life_days": (
                list(
                    stage10
                    .visible_damage_half_life_days
                )
            ),
            "selection_guardrails": (
                asdict(
                    stage10.selection
                )
            ),
        },
        "control_summary": (
            asdict(
                control
            )
        ),
        "candidate_summaries": [
            asdict(
                summary
            )
            for summary in summaries
        ],
        "selected_candidate": (
            asdict(
                next(
                    candidate
                    for candidate in candidates
                    if candidate.candidate_id
                    == selected.candidate_id
                )
            )
        ),
        "selected_summary": (
            asdict(
                selected
            )
        ),
        "decision": (
            decision
        ),
        "next_direction_if_control_retained": (
            "MRI observation model / multimodal information"
        ),
        "patient_candidate_results": [
            asdict(
                row
            )
            for row in rows
        ],
        "selected_patient_results": [
            asdict(
                row
            )
            for row in (
                selected_rows
            )
        ],
    }

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=(
                destination.parent
            ),
            prefix=(
                f".{destination.name}-"
            ),
        )
    )

    try:
        manifest_path = (
            temporary
            / "stage10_decoupled_selection.json"
        )

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

        (
            temporary
            / "stage10_decoupled_selection.sha256"
        ).write_text(
            (
                sha256_file(
                    manifest_path
                )
                + "  stage10_decoupled_selection.json\n"
            ),
            encoding="ascii",
        )

        _write_csv(
            temporary
            / "stage10_decoupled_selection.csv",
            rows,
        )

        temporary.rename(
            destination
        )

    except BaseException:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    return Stage10SelectionArtifact(
        directory=destination,
        manifest=payload,
    )
