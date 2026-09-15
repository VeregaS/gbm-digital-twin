from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.evaluation.metrics import dice_score, relative_volume_error
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.prediction import load_frozen_v2_prediction


@dataclass(frozen=True)
class FrozenV2EvaluationResult:
    patient_id: int
    target_timepoint: str
    target_day: float
    prediction_dice: float
    prediction_volume_error: float
    persistence_dice: float
    persistence_volume_error: float
    volume_baseline_dice: float
    volume_baseline_volume_error: float


def evaluate_frozen_v2_prediction(
    *,
    artifact_dir: Path,
    observed_target: PreparedPatientTimepoint,
) -> FrozenV2EvaluationResult:
    artifact = load_frozen_v2_prediction(artifact_dir)
    manifest = artifact.manifest
    horizon = manifest["prediction_horizon"]
    geometry = manifest["geometry"]

    if observed_target.patient_id != manifest["patient_id"]:
        raise ValueError("Observed target belongs to a different patient")

    if observed_target.name != horizon["target_timepoint"]:
        raise ValueError("Observed target timepoint does not match frozen horizon")

    if not math.isclose(
        observed_target.days_from_baseline,
        horizon["target_day"],
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        raise ValueError("Observed target day does not match frozen horizon")

    if observed_target.gtv.shape != tuple(geometry["shape"]):
        raise ValueError("Observed target shape does not match frozen geometry")

    if not np.allclose(observed_target.gtv.spacing, geometry["spacing"], atol=1e-5):
        raise ValueError("Observed target spacing does not match frozen geometry")

    if not np.allclose(observed_target.gtv.affine, geometry["affine"], atol=1e-5):
        raise ValueError("Observed target affine does not match frozen geometry")

    threshold = manifest["parameters"]["observation_threshold"]
    observed_mask = observed_target.gtv.data > threshold

    return FrozenV2EvaluationResult(
        patient_id=observed_target.patient_id,
        target_timepoint=observed_target.name,
        target_day=observed_target.days_from_baseline,
        prediction_dice=dice_score(artifact.prediction_mask, observed_mask),
        prediction_volume_error=relative_volume_error(
            artifact.prediction_mask,
            observed_mask,
        ),
        persistence_dice=dice_score(artifact.persistence_mask, observed_mask),
        persistence_volume_error=relative_volume_error(
            artifact.persistence_mask,
            observed_mask,
        ),
        volume_baseline_dice=dice_score(
            artifact.volume_baseline_mask,
            observed_mask,
        ),
        volume_baseline_volume_error=relative_volume_error(
            artifact.volume_baseline_mask,
            observed_mask,
        ),
    )
