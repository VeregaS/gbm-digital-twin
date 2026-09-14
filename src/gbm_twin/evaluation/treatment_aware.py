from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.calibration.grid_search import (
    CalibrationObjective,
)
from gbm_twin.calibration.refinement import (
    adaptive_grid_search,
)
from gbm_twin.data.cfb_metadata import (
    CFBMetadata,
)
from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)
from gbm_twin.data.nifti import (
    same_geometry,
)
from gbm_twin.data.patient_loader import (
    load_patient_timepoint,
)
from gbm_twin.evaluation.config import (
    CohortExperimentConfig,
)
from gbm_twin.evaluation.metrics import (
    dice_score,
    relative_volume_error,
)
from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    build_computational_domain,
    initial_condition_from_gtv,
)
from gbm_twin.models.rt_schedule import (
    build_fractionated_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.preprocessing.resampling import (
    resample_volume,
)


@dataclass(frozen=True)
class TreatmentAwareEvaluationResult:
    patient_id: int

    alpha_per_gy: float
    alpha_beta_ratio_gy: float

    calibration_objective: CalibrationObjective
    soft_temperature: float

    rt_total_dose_gy: float
    rt_fractions: int
    rt_dose_per_fraction_gy: float
    rt_start_day: float
    rt_last_fraction_day: float

    dt01: int
    dt12: int
    post_rt_gap_to_t1_days: float

    diffusion: float
    proliferation: float

    calibration_dice: float
    calibration_volume_error: float
    calibration_loss: float

    coarse_diffusion: float
    coarse_proliferation: float

    prediction_dice: float
    prediction_volume_error: float

    persistence_dice: float
    persistence_volume_error: float


def evaluate_treatment_aware_patient(
    patient_id: int,
    *,
    experiment: CohortExperimentConfig,
    metadata: CFBMetadata,
    treatment_metadata: CFBTreatmentMetadata,
    alpha_per_gy: float,
    alpha_beta_ratio_gy: float = 10.0,
    cache_dir: Path | None = None,
    workers: int = 1,
    calibration_objective: CalibrationObjective = "hard",
    soft_temperature: float = 0.05,
) -> TreatmentAwareEvaluationResult:
    if alpha_per_gy < 0:
        raise ValueError(
            "alpha_per_gy must be non-negative"
        )

    if alpha_beta_ratio_gy <= 0:
        raise ValueError(
            "alpha_beta_ratio_gy must be positive"
        )

    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    patient = metadata.patient(
        patient_id
    )

    t0 = load_patient_timepoint(
        experiment.patients_root,
        patient_id,
        patient.get_timepoint("t0"),
    )

    t1 = load_patient_timepoint(
        experiment.patients_root,
        patient_id,
        patient.get_timepoint("t1"),
    )

    t0_gtv = resample_volume(
        t0.gtv,
        experiment.evaluation.target_spacing,
        is_mask=True,
    )

    t1_gtv = resample_volume(
        t1.gtv,
        experiment.evaluation.target_spacing,
        is_mask=True,
    )

    t0_brain = resample_volume(
        t0.brain_mask,
        experiment.evaluation.target_spacing,
        is_mask=True,
    )

    if not same_geometry(
        t0_gtv,
        t1_gtv,
    ):
        raise ValueError(
            f"Patient {patient_id}: "
            "t0/t1 geometry mismatch"
        )

    if not same_geometry(
        t0_gtv,
        t0_brain,
    ):
        raise ValueError(
            f"Patient {patient_id}: "
            "t0 GTV / brain geometry mismatch"
        )

    dt01 = patient.interval_days(
        "t0",
        "t1",
    )

    calibration_domain = (
        build_computational_domain(
            t0_brain.data,
            t0_gtv.data,
        )
    )

    calibration_initial = (
        initial_condition_from_gtv(
            t0_gtv.data,
            calibration_domain,
            threshold=(
                experiment
                .evaluation
                .threshold
            ),
        )
    )

    observed_t1 = (
        t1_gtv.data
        > experiment.evaluation.threshold
    )

    treatment_record = (
        treatment_metadata.treatment(
            patient_id
        )
    )

    if treatment_record is None:
        raise ValueError(
            f"Patient {patient_id}: "
            "missing treatment metadata"
        )

    rt_start_day = (
        treatment_record
        .radiotherapy_start_day
    )

    total_dose_gy = (
        treatment_record.dose_gy
    )

    fractions_number = (
        treatment_record.fractions_number
    )

    if (
        rt_start_day is None
        or total_dose_gy is None
        or fractions_number is None
    ):
        raise ValueError(
            f"Patient {patient_id}: "
            "incomplete RT metadata"
        )

    schedule = (
        reconstruct_weekday_like_schedule(
            start_day=rt_start_day,
            total_dose_gy=total_dose_gy,
            fractions_number=fractions_number,
        )
    )

    last_fraction_day = (
        schedule.fraction_days[-1]
    )

    if last_fraction_day > dt01:
        raise ValueError(
            f"Patient {patient_id}: "
            "reconstructed RT is not complete "
            "by t1"
        )

    radiobiology = (
        RadiobiologyParameters(
            alpha_per_gy=alpha_per_gy,
            alpha_beta_ratio_gy=(
                alpha_beta_ratio_gy
            ),
        )
    )

    treatment = (
        build_fractionated_radiotherapy(
            schedule,
            radiobiology,
        )
    )

    calibration = adaptive_grid_search(
        calibration_initial,
        observed_t1,
        calibration_domain,
        spacing=t0_gtv.spacing,
        duration_days=float(dt01),
        dt=experiment.evaluation.dt,
        diffusion_values=list(
            experiment
            .evaluation
            .diffusion_values
        ),
        proliferation_values=list(
            experiment
            .evaluation
            .proliferation_values
        ),
        threshold=(
            experiment.evaluation.threshold
        ),
        volume_weight=(
            experiment
            .evaluation
            .volume_weight
        ),
        treatment=treatment,
        start_time_day=0.0,
        cache_dir=cache_dir,
        workers=workers,
        objective=calibration_objective,
        soft_temperature=soft_temperature,
    )

    best = calibration.best

    # t2 is intentionally loaded only after calibration.
    t2 = load_patient_timepoint(
        experiment.patients_root,
        patient_id,
        patient.get_timepoint("t2"),
    )

    t2_gtv = resample_volume(
        t2.gtv,
        experiment.evaluation.target_spacing,
        is_mask=True,
    )

    t1_brain = resample_volume(
        t1.brain_mask,
        experiment.evaluation.target_spacing,
        is_mask=True,
    )

    if not same_geometry(
        t1_gtv,
        t2_gtv,
    ):
        raise ValueError(
            f"Patient {patient_id}: "
            "t1/t2 geometry mismatch"
        )

    if not same_geometry(
        t1_gtv,
        t1_brain,
    ):
        raise ValueError(
            f"Patient {patient_id}: "
            "t1 GTV / brain geometry mismatch"
        )

    dt12 = patient.interval_days(
        "t1",
        "t2",
    )

    prediction_domain = (
        build_computational_domain(
            t1_brain.data,
            t1_gtv.data,
        )
    )

    prediction_initial = (
        initial_condition_from_gtv(
            t1_gtv.data,
            prediction_domain,
            threshold=(
                experiment
                .evaluation
                .threshold
            ),
        )
    ).astype(
        np.float32,
        copy=False,
    )

    prediction_params = (
        ReactionDiffusionParameters(
            diffusion=best.diffusion,
            proliferation=(
                best.proliferation
            ),
        )
    )

    predicted_field = (
        simulate_reaction_diffusion(
            prediction_initial,
            prediction_params,
            spacing=t1_gtv.spacing,
            duration_days=float(dt12),
            dt=experiment.evaluation.dt,
            domain_mask=prediction_domain,
            treatment=treatment,
            start_time_day=float(dt01),
        )
    )

    predicted_t2 = (
        predicted_field
        >= experiment.evaluation.threshold
    )

    observed_t2 = (
        t2_gtv.data
        > experiment.evaluation.threshold
    )

    persistence_t2 = (
        t1_gtv.data
        > experiment.evaluation.threshold
    )

    return TreatmentAwareEvaluationResult(
        patient_id=patient_id,
        alpha_per_gy=alpha_per_gy,
        alpha_beta_ratio_gy=(
            alpha_beta_ratio_gy
        ),
        calibration_objective=(
            calibration_objective
        ),
        soft_temperature=soft_temperature,
        rt_total_dose_gy=(
            schedule.total_dose_gy
        ),
        rt_fractions=(
            schedule.fractions_number
        ),
        rt_dose_per_fraction_gy=(
            schedule.total_dose_gy
            / schedule.fractions_number
        ),
        rt_start_day=(
            schedule.start_day
        ),
        rt_last_fraction_day=(
            last_fraction_day
        ),
        dt01=dt01,
        dt12=dt12,
        post_rt_gap_to_t1_days=(
            float(dt01)
            - last_fraction_day
        ),
        diffusion=best.diffusion,
        proliferation=(
            best.proliferation
        ),
        calibration_dice=best.dice,
        calibration_volume_error=(
            best.volume_error
        ),
        calibration_loss=best.loss,
        coarse_diffusion=(
            calibration
            .coarse_best
            .diffusion
        ),
        coarse_proliferation=(
            calibration
            .coarse_best
            .proliferation
        ),
        prediction_dice=dice_score(
            predicted_t2,
            observed_t2,
        ),
        prediction_volume_error=(
            relative_volume_error(
                predicted_t2,
                observed_t2,
            )
        ),
        persistence_dice=dice_score(
            persistence_t2,
            observed_t2,
        ),
        persistence_volume_error=(
            relative_volume_error(
                persistence_t2,
                observed_t2,
            )
        ),
    )