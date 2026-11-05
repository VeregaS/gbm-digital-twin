from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import numpy as np

from gbm_twin.evaluation.metrics import (
    centroid_distance_mm,
    dice_score,
    hausdorff95_mm,
    relative_volume_error,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)
from gbm_twin.workflows.prediction import (
    FrozenPredictionArtifact,
    load_frozen_v2_prediction,
    load_frozen_v3_prediction,
)


@dataclass(frozen=True)
class FrozenV2EvaluationResult:
    patient_id: int
    target_timepoint: str
    target_day: float

    prediction_dice: float
    prediction_volume_error: float
    prediction_hd95_mm: float | None
    prediction_centroid_distance_mm: float | None

    persistence_dice: float
    persistence_volume_error: float
    persistence_hd95_mm: float | None
    persistence_centroid_distance_mm: float | None

    volume_baseline_dice: float
    volume_baseline_volume_error: float
    volume_baseline_hd95_mm: float | None
    volume_baseline_centroid_distance_mm: float | None


FrozenV3EvaluationResult = FrozenV2EvaluationResult

ArtifactLoader = Callable[
    [Path],
    FrozenPredictionArtifact,
]


def _require_mapping(
    mapping: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = mapping.get(key)

    if not isinstance(value, dict):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _require_string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be a string"
        )

    return value


def _require_int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(key)

    if type(value) is not int:
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be an integer"
        )

    return cast(
        int,
        value,
    )


def _require_float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(key)

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be numeric"
        )

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be finite"
        )

    return result


def _require_shape(
    mapping: dict[str, object],
    key: str,
) -> tuple[int, ...]:
    value = mapping.get(key)

    if not isinstance(value, list):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be a list"
        )

    raw_values = cast(
        list[object],
        value,
    )

    result: list[int] = []

    for raw_value in raw_values:
        if type(raw_value) is not int:
            raise ValueError(
                "Prediction manifest field "
                f"{key!r} must contain integers"
            )

        result.append(
            cast(
                int,
                raw_value,
            )
        )

    return tuple(result)


def _require_spacing(
    mapping: dict[str, object],
    key: str,
) -> tuple[
    float,
    float,
    float,
]:
    value = mapping.get(key)

    if not isinstance(value, list):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be a list"
        )

    raw_values = cast(
        list[object],
        value,
    )

    if len(raw_values) != 3:
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must contain three values"
        )

    result: list[float] = []

    for raw_value in raw_values:
        if (
            isinstance(raw_value, bool)
            or not isinstance(
                raw_value,
                (int, float),
            )
        ):
            raise ValueError(
                "Prediction manifest field "
                f"{key!r} must contain numbers"
            )

        converted = float(raw_value)

        if (
            not math.isfinite(converted)
            or converted <= 0.0
        ):
            raise ValueError(
                "Prediction manifest field "
                f"{key!r} must contain "
                "finite positive values"
            )

        result.append(converted)

    return (
        result[0],
        result[1],
        result[2],
    )


def _require_affine(
    mapping: dict[str, object],
    key: str,
) -> np.ndarray:
    value = mapping.get(key)

    if value is None:
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} is missing"
        )

    try:
        affine = np.asarray(
            value,
            dtype=np.float64,
        )
    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be numeric"
        ) from exc

    if affine.shape != (
        4,
        4,
    ):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must be a 4x4 matrix"
        )

    if not np.all(
        np.isfinite(
            affine
        )
    ):
        raise ValueError(
            "Prediction manifest field "
            f"{key!r} must contain "
            "finite values"
        )

    return affine


def _evaluate_frozen_prediction(
    *,
    artifact_dir: Path,
    observed_target: PreparedPatientTimepoint,
    loader: ArtifactLoader,
) -> FrozenV2EvaluationResult:
    artifact = loader(
        artifact_dir
    )

    manifest = cast(
        dict[str, object],
        artifact.manifest,
    )

    patient_id = _require_int(
        manifest,
        "patient_id",
    )

    horizon = _require_mapping(
        manifest,
        "prediction_horizon",
    )

    geometry = _require_mapping(
        manifest,
        "geometry",
    )

    parameters = _require_mapping(
        manifest,
        "parameters",
    )

    target_timepoint = (
        _require_string(
            horizon,
            "target_timepoint",
        )
    )

    target_day = _require_float(
        horizon,
        "target_day",
    )

    expected_shape = (
        _require_shape(
            geometry,
            "shape",
        )
    )

    expected_spacing = (
        _require_spacing(
            geometry,
            "spacing",
        )
    )

    expected_affine = (
        _require_affine(
            geometry,
            "affine",
        )
    )

    threshold = _require_float(
        parameters,
        "observation_threshold",
    )

    if (
        observed_target.patient_id
        != patient_id
    ):
        raise ValueError(
            "Observed target belongs "
            "to a different patient"
        )

    if (
        observed_target.name
        != target_timepoint
    ):
        raise ValueError(
            "Observed target timepoint "
            "does not match frozen horizon"
        )

    if not math.isclose(
        observed_target.days_from_baseline,
        target_day,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError(
            "Observed target day does "
            "not match frozen horizon"
        )

    if (
        observed_target.gtv.shape
        != expected_shape
    ):
        raise ValueError(
            "Observed target shape does "
            "not match frozen geometry"
        )

    if not np.allclose(
        observed_target.gtv.spacing,
        expected_spacing,
        atol=1e-5,
    ):
        raise ValueError(
            "Observed target spacing does "
            "not match frozen geometry"
        )

    if not np.allclose(
        observed_target.gtv.affine,
        expected_affine,
        atol=1e-5,
    ):
        raise ValueError(
            "Observed target affine does "
            "not match frozen geometry"
        )

    observed_mask = (
        observed_target.gtv.data
        > threshold
    )

    spacing = (
        observed_target.gtv.spacing
    )

    return FrozenV2EvaluationResult(
        patient_id=(
            observed_target.patient_id
        ),
        target_timepoint=(
            observed_target.name
        ),
        target_day=(
            observed_target
            .days_from_baseline
        ),
        prediction_dice=dice_score(
            artifact.prediction_mask,
            observed_mask,
        ),
        prediction_volume_error=(
            relative_volume_error(
                artifact.prediction_mask,
                observed_mask,
            )
        ),
        prediction_hd95_mm=(
            hausdorff95_mm(
                artifact.prediction_mask,
                observed_mask,
                spacing=spacing,
            )
        ),
        prediction_centroid_distance_mm=(
            centroid_distance_mm(
                artifact.prediction_mask,
                observed_mask,
                spacing=spacing,
            )
        ),
        persistence_dice=dice_score(
            artifact.persistence_mask,
            observed_mask,
        ),
        persistence_volume_error=(
            relative_volume_error(
                artifact.persistence_mask,
                observed_mask,
            )
        ),
        persistence_hd95_mm=(
            hausdorff95_mm(
                artifact.persistence_mask,
                observed_mask,
                spacing=spacing,
            )
        ),
        persistence_centroid_distance_mm=(
            centroid_distance_mm(
                artifact.persistence_mask,
                observed_mask,
                spacing=spacing,
            )
        ),
        volume_baseline_dice=(
            dice_score(
                artifact.volume_baseline_mask,
                observed_mask,
            )
        ),
        volume_baseline_volume_error=(
            relative_volume_error(
                artifact.volume_baseline_mask,
                observed_mask,
            )
        ),
        volume_baseline_hd95_mm=(
            hausdorff95_mm(
                artifact.volume_baseline_mask,
                observed_mask,
                spacing=spacing,
            )
        ),
        volume_baseline_centroid_distance_mm=(
            centroid_distance_mm(
                artifact.volume_baseline_mask,
                observed_mask,
                spacing=spacing,
            )
        ),
    )


def evaluate_frozen_v2_prediction(
    *,
    artifact_dir: Path,
    observed_target: PreparedPatientTimepoint,
) -> FrozenV2EvaluationResult:
    return _evaluate_frozen_prediction(
        artifact_dir=artifact_dir,
        observed_target=observed_target,
        loader=load_frozen_v2_prediction,
    )


def evaluate_frozen_v3_prediction(
    *,
    artifact_dir: Path,
    observed_target: PreparedPatientTimepoint,
) -> FrozenV3EvaluationResult:
    return _evaluate_frozen_prediction(
        artifact_dir=artifact_dir,
        observed_target=observed_target,
        loader=load_frozen_v3_prediction,
    )
