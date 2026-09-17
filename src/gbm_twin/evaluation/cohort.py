from dataclasses import dataclass
from pathlib import Path

from gbm_twin.calibration.grid_search import grid_search
from gbm_twin.data.cfb_metadata import CFBMetadata
from gbm_twin.data.nifti import same_geometry
from gbm_twin.data.patient_loader import load_patient_timepoint
from gbm_twin.evaluation.baselines import (
    extrapolate_volume,
    resize_mask_to_volume,
)
from gbm_twin.evaluation.metrics import (
    dice_score,
    mask_volume_cm3,
    relative_volume_error,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    build_computational_domain,
    initial_condition_from_gtv,
)
from gbm_twin.models.solver import simulate_reaction_diffusion
from gbm_twin.preprocessing.resampling import resample_volume

RAW_RESULT_COLUMNS = (
    "patient_id",
    "dt01",
    "dt12",
    "volume_t0_cm3",
    "volume_t1_cm3",
    "volume_t2_cm3",
    "D",
    "rho",
    "calibration_dice",
    "calibration_volume_error",
    "calibration_loss",
    "twin_dice",
    "twin_volume_error",
    "persistence_dice",
    "persistence_volume_error",
    "predicted_volume_t2_cm3",
    "morphological_dice",
    "morphological_volume_error",
)


@dataclass(frozen=True)
class EvaluationConfig:
    target_spacing: tuple[float, float, float] = (
        2.0,
        2.0,
        2.0,
    )

    threshold: float = 0.5
    dt: float = 2.0

    diffusion_values: tuple[float, ...] = (
        0.005,
        0.015,
        0.030,
    )

    proliferation_values: tuple[float, ...] = (
        0.015,
        0.035,
        0.055,
    )

    volume_weight: float = 0.5
    refinement_rounds: int = 1
    upper_boundary_expansion_factor: float = 0.5


def evaluate_patient(
    patient_id: int,
    metadata: CFBMetadata,
    patients_root: Path,
    config: EvaluationConfig,
) -> dict[str, float | int]:
    patient = metadata.patient(patient_id)

    t0 = load_patient_timepoint(
        patients_root,
        patient_id,
        patient.get_timepoint("t0"),
    )

    t1 = load_patient_timepoint(
        patients_root,
        patient_id,
        patient.get_timepoint("t1"),
    )

    t2 = load_patient_timepoint(
        patients_root,
        patient_id,
        patient.get_timepoint("t2"),
    )

    t0_gtv = resample_volume(
        t0.gtv,
        config.target_spacing,
        is_mask=True,
    )

    t1_gtv = resample_volume(
        t1.gtv,
        config.target_spacing,
        is_mask=True,
    )

    t2_gtv = resample_volume(
        t2.gtv,
        config.target_spacing,
        is_mask=True,
    )

    t0_brain = resample_volume(
        t0.brain_mask,
        config.target_spacing,
        is_mask=True,
    )

    t1_brain = resample_volume(
        t1.brain_mask,
        config.target_spacing,
        is_mask=True,
    )

    if not same_geometry(t0_gtv, t1_gtv):
        raise ValueError(
            f"Patient {patient_id}: t0/t1 geometry mismatch"
        )

    if not same_geometry(t1_gtv, t2_gtv):
        raise ValueError(
            f"Patient {patient_id}: t1/t2 geometry mismatch"
        )

    dt01 = patient.interval_days(
        "t0",
        "t1",
    )

    dt12 = patient.interval_days(
        "t1",
        "t2",
    )

    volume_t0 = mask_volume_cm3(
        t0_gtv
    )

    volume_t1 = mask_volume_cm3(
        t1_gtv
    )

    volume_t2 = mask_volume_cm3(
        t2_gtv
    )

    # ---------------------------------------------------------
    # Calibration: t0 -> t1
    # ---------------------------------------------------------

    domain_t0 = build_computational_domain(
        t0_brain.data,
        t0_gtv.data,
    )

    initial_t0 = initial_condition_from_gtv(
        t0_gtv.data,
        domain_t0,
        threshold=config.threshold,
    )

    observed_t1 = (
        t1_gtv.data
        > config.threshold
    )

    calibration_results = grid_search(
        initial_t0,
        observed_t1,
        domain_t0,
        spacing=t0_gtv.spacing,
        duration_days=float(dt01),
        dt=config.dt,
        diffusion_values=list(
            config.diffusion_values
        ),
        proliferation_values=list(
            config.proliferation_values
        ),
        threshold=config.threshold,
        volume_weight=config.volume_weight,
    )

    best = calibration_results[0]

    params = ReactionDiffusionParameters(
        diffusion=best.diffusion,
        proliferation=best.proliferation,
    )

    # ---------------------------------------------------------
    # Digital Twin prediction: t1 -> t2
    # ---------------------------------------------------------

    domain_t1 = build_computational_domain(
        t1_brain.data,
        t1_gtv.data,
    )

    initial_t1 = initial_condition_from_gtv(
        t1_gtv.data,
        domain_t1,
        threshold=config.threshold,
    )

    concentration_t2 = simulate_reaction_diffusion(
        initial_t1,
        params,
        spacing=t1_gtv.spacing,
        duration_days=float(dt12),
        dt=config.dt,
        domain_mask=domain_t1,
    )

    predicted_t2 = (
        concentration_t2
        >= config.threshold
    )

    observed_t2 = (
        t2_gtv.data
        > config.threshold
    )

    twin_dice = dice_score(
        predicted_t2,
        observed_t2,
    )

    twin_volume_error = relative_volume_error(
        predicted_t2,
        observed_t2,
    )

    # ---------------------------------------------------------
    # Persistence baseline
    # ---------------------------------------------------------

    persistence_prediction = (
        t1_gtv.data
        > config.threshold
    )

    persistence_dice = dice_score(
        persistence_prediction,
        observed_t2,
    )

    persistence_volume_error = (
        relative_volume_error(
            persistence_prediction,
            observed_t2,
        )
    )

    # ---------------------------------------------------------
    # Volume-growth baseline
    # ---------------------------------------------------------

    predicted_volume_t2 = extrapolate_volume(
        volume_t0,
        volume_t1,
        dt01_days=float(dt01),
        dt12_days=float(dt12),
    )

    # ---------------------------------------------------------
    # Morphological baseline
    # ---------------------------------------------------------

    morphological_prediction = (
        resize_mask_to_volume(
            persistence_prediction,
            target_volume_cm3=(
                predicted_volume_t2
            ),
            spacing=t1_gtv.spacing,
        )
    )

    morphological_dice = dice_score(
        morphological_prediction,
        observed_t2,
    )

    morphological_volume_error = (
        relative_volume_error(
            morphological_prediction,
            observed_t2,
        )
    )

    return {
        "patient_id": patient_id,
        "dt01": dt01,
        "dt12": dt12,
        "volume_t0_cm3": volume_t0,
        "volume_t1_cm3": volume_t1,
        "volume_t2_cm3": volume_t2,
        "D": best.diffusion,
        "rho": best.proliferation,
        "calibration_dice": best.dice,
        "calibration_volume_error": (
            best.volume_error
        ),
        "calibration_loss": best.loss,
        "twin_dice": twin_dice,
        "twin_volume_error": (
            twin_volume_error
        ),
        "persistence_dice": (
            persistence_dice
        ),
        "persistence_volume_error": (
            persistence_volume_error
        ),
        "predicted_volume_t2_cm3": (
            predicted_volume_t2
        ),
        "morphological_dice": (
            morphological_dice
        ),
        "morphological_volume_error": (
            morphological_volume_error
        ),
    }
