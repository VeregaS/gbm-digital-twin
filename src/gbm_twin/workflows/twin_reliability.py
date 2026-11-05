from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np
from scipy.ndimage import label as connected_components

from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.patients import prepare_patient_timepoint
from gbm_twin.workflows.twin_artifacts import (
    find_evaluated_patient,
    load_frozen_patient_artifact,
    target_spacing,
)

ForecastReliabilityStatus = Literal[
    "nominal",
    "caution",
    "limited",
]

ForecastReliabilityFactorLevel = Literal[
    "caution",
    "limited",
]


@dataclass(frozen=True)
class ForecastReliabilityFactor:
    code: str
    level: ForecastReliabilityFactorLevel
    message: str


@dataclass(frozen=True)
class TwinForecastReliability:
    patient_id: int
    status: ForecastReliabilityStatus
    model_version: str
    protocol_version: str
    sealed: bool
    source_git_commit_sha: str
    source_git_dirty: bool
    forecast_horizon_days: float
    calibration_identifiable: bool
    diffusion_at_boundary: bool
    proliferation_at_boundary: bool
    prediction_empty: bool
    prediction_component_count: int
    prediction_largest_component_fraction: float | None
    prediction_outside_brain_fraction: float | None
    factors: tuple[
        ForecastReliabilityFactor,
        ...,
    ]
    interpretation: str = (
        "Pre-t2 research quality gate derived only from frozen calibration "
        "diagnostics and the frozen prediction relative to the t1 brain mask. "
        "It is not a calibrated probability of forecast correctness."
    )


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


def _string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(
        key
    )

    if not isinstance(
        value,
        str,
    ):
        raise ValueError(
            f"{key} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{key} must not be empty"
        )

    return normalized


def _bool(
    mapping: dict[str, object],
    key: str,
) -> bool:
    value = mapping.get(
        key
    )

    if type(
        value
    ) is not bool:
        raise ValueError(
            f"{key} must be a boolean"
        )

    return cast(
        bool,
        value,
    )


def _float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(
        key
    )

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
            f"{key} must be numeric"
        )

    result = float(
        value
    )

    if not np.isfinite(
        result
    ):
        raise ValueError(
            f"{key} must be finite"
        )

    return result


def _component_statistics(
    mask: np.ndarray,
) -> tuple[
    int,
    float | None,
]:
    binary = np.asarray(
        mask,
        dtype=bool,
    )

    count = int(
        np.count_nonzero(
            binary
        )
    )

    if count == 0:
        return (
            0,
            None,
        )

    labels = np.zeros(
        binary.shape,
        dtype=np.int32,
    )

    connected_components(
        binary,
        output=labels,
    )

    component_count = int(
        labels.max()
    )

    if component_count <= 0:
        return (
            0,
            None,
        )

    sizes = np.bincount(
        labels.reshape(
            -1
        )
    )[
        1 : component_count + 1
    ]

    largest = int(
        sizes.max()
    )

    return (
        component_count,
        float(
            largest
            / count
        ),
    )


def assess_forecast_reliability(
    *,
    patient_id: int,
    model_version: str,
    protocol_version: str,
    sealed: bool,
    source_git_commit_sha: str,
    source_git_dirty: bool,
    forecast_horizon_days: float,
    calibration_identifiable: bool,
    diffusion_at_boundary: bool,
    proliferation_at_boundary: bool,
    prediction_mask: np.ndarray,
    brain_mask: np.ndarray,
) -> TwinForecastReliability:
    prediction = np.asarray(
        prediction_mask,
        dtype=bool,
    )

    brain = np.asarray(
        brain_mask,
        dtype=bool,
    )

    if (
        prediction.ndim != 3
        or brain.ndim != 3
    ):
        raise ValueError(
            "prediction_mask and brain_mask must be 3D"
        )

    if (
        prediction.shape
        != brain.shape
    ):
        raise ValueError(
            "prediction_mask and brain_mask must share shape"
        )

    (
        component_count,
        largest_component_fraction,
    ) = _component_statistics(
        prediction
    )

    voxel_count = int(
        np.count_nonzero(
            prediction
        )
    )

    outside_voxels = int(
        np.count_nonzero(
            prediction
            & ~brain
        )
    )

    outside_fraction = (
        None
        if voxel_count == 0
        else float(
            outside_voxels
            / voxel_count
        )
    )

    factors: list[
        ForecastReliabilityFactor
    ] = []

    if not calibration_identifiable:
        factors.append(
            ForecastReliabilityFactor(
                code=(
                    "calibration_non_identifiable"
                ),
                level="limited",
                message=(
                    "D and rho were not uniquely bracketed by the "
                    "pre-t2 calibration search."
                ),
            )
        )

    if diffusion_at_boundary:
        factors.append(
            ForecastReliabilityFactor(
                code="diffusion_at_boundary",
                level="caution",
                message=(
                    "The selected diffusion parameter lies on the "
                    "evaluated search boundary."
                ),
            )
        )

    if proliferation_at_boundary:
        factors.append(
            ForecastReliabilityFactor(
                code=(
                    "proliferation_at_boundary"
                ),
                level="caution",
                message=(
                    "The selected proliferation parameter lies on the "
                    "evaluated search boundary."
                ),
            )
        )

    prediction_empty = (
        voxel_count == 0
    )

    if prediction_empty:
        factors.append(
            ForecastReliabilityFactor(
                code="prediction_empty",
                level="limited",
                message=(
                    "The frozen prediction contains no positive tumor voxels."
                ),
            )
        )

    if (
        outside_fraction is not None
        and outside_fraction > 0.001
    ):
        factors.append(
            ForecastReliabilityFactor(
                code=(
                    "prediction_outside_t1_brain"
                ),
                level="limited",
                message=(
                    "More than 0.1% of frozen prediction voxels lie outside "
                    "the t1 brain mask."
                ),
            )
        )

    if (
        component_count > 1
        and largest_component_fraction
        is not None
        and largest_component_fraction
        < 0.95
    ):
        factors.append(
            ForecastReliabilityFactor(
                code="prediction_fragmented",
                level="caution",
                message=(
                    "The frozen prediction contains multiple spatially "
                    "separated components."
                ),
            )
        )

    if source_git_dirty:
        factors.append(
            ForecastReliabilityFactor(
                code="dirty_source_tree",
                level="caution",
                message=(
                    "The frozen prediction provenance reports a dirty Git "
                    "working tree."
                ),
            )
        )

    if any(
        factor.level
        == "limited"
        for factor in factors
    ):
        status: ForecastReliabilityStatus = (
            "limited"
        )

    elif factors:
        status = "caution"

    else:
        status = "nominal"

    return TwinForecastReliability(
        patient_id=patient_id,
        status=status,
        model_version=model_version,
        protocol_version=protocol_version,
        sealed=sealed,
        source_git_commit_sha=(
            source_git_commit_sha
        ),
        source_git_dirty=(
            source_git_dirty
        ),
        forecast_horizon_days=(
            forecast_horizon_days
        ),
        calibration_identifiable=(
            calibration_identifiable
        ),
        diffusion_at_boundary=(
            diffusion_at_boundary
        ),
        proliferation_at_boundary=(
            proliferation_at_boundary
        ),
        prediction_empty=(
            prediction_empty
        ),
        prediction_component_count=(
            component_count
        ),
        prediction_largest_component_fraction=(
            largest_component_fraction
        ),
        prediction_outside_brain_fraction=(
            outside_fraction
        ),
        factors=tuple(
            factors
        ),
    )


def get_twin_forecast_reliability(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    patient_id: int,
) -> TwinForecastReliability:
    evaluation = (
        load_sealed_cohort_evaluation(
            cohort_evaluation_root
        )
    )

    payload = (
        evaluation.manifest
    )

    find_evaluated_patient(
        payload,
        patient_id,
    )

    spacing = target_spacing(
        payload
    )

    t1 = prepare_patient_timepoint(
        metadata_root=metadata_root,
        patients_root=patients_root,
        patient_id=patient_id,
        timepoint_name="t1",
        target_spacing=spacing,
    )

    artifact = (
        load_frozen_patient_artifact(
            cohort_freeze_root=(
                cohort_freeze_root
            ),
            payload=payload,
            patient_id=patient_id,
        )
    )

    manifest = cast(
        dict[str, object],
        artifact.manifest,
    )

    calibration = _mapping(
        manifest,
        "calibration",
    )

    diagnostics = _mapping(
        calibration,
        "diagnostics",
    )

    horizon = _mapping(
        manifest,
        "prediction_horizon",
    )

    provenance = _mapping(
        manifest,
        "provenance",
    )

    return assess_forecast_reliability(
        patient_id=patient_id,
        model_version=_string(
            manifest,
            "model_version",
        ),
        protocol_version=_string(
            manifest,
            "protocol_version",
        ),
        sealed=_bool(
            manifest,
            "sealed",
        ),
        source_git_commit_sha=(
            _string(
                provenance,
                "git_commit_sha",
            )
        ),
        source_git_dirty=_bool(
            provenance,
            "git_dirty",
        ),
        forecast_horizon_days=(
            _float(
                horizon,
                "duration_days",
            )
        ),
        calibration_identifiable=(
            _bool(
                diagnostics,
                "identifiable",
            )
        ),
        diffusion_at_boundary=(
            _bool(
                diagnostics,
                "diffusion_at_boundary",
            )
        ),
        proliferation_at_boundary=(
            _bool(
                diagnostics,
                "proliferation_at_boundary",
            )
        ),
        prediction_mask=(
            artifact.prediction_mask
        ),
        brain_mask=(
            t1.brain_mask.data
            > 0.5
        ),
    )
