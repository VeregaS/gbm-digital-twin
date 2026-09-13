from pathlib import Path

import numpy as np

from gbm_twin.data.models import Timepoint
from gbm_twin.data.nifti import same_geometry
from gbm_twin.data.patient_loader import load_patient_timepoint
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


def main() -> None:
    root = Path(r"D:\Datasets\CFB-GBM\patients")

    target_spacing = (2.0, 2.0, 2.0)

    # Calibrated ONLY on t0 -> t1.
    params = ReactionDiffusionParameters(
        diffusion=0.0125,
        proliferation=0.0450,
    )

    # Prediction starts from observed t1.
    t1 = load_patient_timepoint(
        root,
        42,
        Timepoint("t1", 77),
    )

    t1_gtv = resample_volume(
        t1.gtv,
        target_spacing,
        is_mask=True,
    )

    t1_brain = resample_volume(
        t1.brain_mask,
        target_spacing,
        is_mask=True,
    )

    domain = build_computational_domain(
        t1_brain.data,
        t1_gtv.data,
    )

    initial = initial_condition_from_gtv(
        t1_gtv.data,
        domain,
    )

    # Real prediction interval:
    # t1 day 77 -> t2 day 189 = 112 days.
    concentration_t2 = simulate_reaction_diffusion(
        initial,
        params,
        spacing=t1_gtv.spacing,
        duration_days=112.0,
        dt=2.0,
        domain_mask=domain,
    )

    predicted_gtv = concentration_t2 >= 0.5

    # t2 is evaluation ONLY.
    t2 = load_patient_timepoint(
        root,
        42,
        Timepoint("t2", 189),
    )

    t2_gtv = resample_volume(
        t2.gtv,
        target_spacing,
        is_mask=True,
    )

    if not same_geometry(t1_gtv, t2_gtv):
        raise ValueError(
            "t1 and t2 computational grids do not match"
        )

    observed_gtv = t2_gtv.data > 0.5
    
    voxel_volume_cm3 = np.prod(t1_gtv.spacing) / 1000.0
    
    # Persistence baseline:
    # assume tumor at t2 is unchanged from t1.
    persistence_gtv = t1_gtv.data > 0.5

    persistence_dice = dice_score(
        persistence_gtv,
        observed_gtv,
    )

    persistence_volume_error = relative_volume_error(
        persistence_gtv,
        observed_gtv,
    )

    persistence_volume = (
        np.count_nonzero(persistence_gtv)
        * voxel_volume_cm3
    )

    dice = dice_score(
        predicted_gtv,
        observed_gtv,
    )

    volume_error = relative_volume_error(
        predicted_gtv,
        observed_gtv,
    )


    predicted_volume = (
        np.count_nonzero(predicted_gtv)
        * voxel_volume_cm3
    )

    observed_volume = mask_volume_cm3(t2_gtv)

    print("Patient: 42")
    print("D:", params.diffusion)
    print("rho:", params.proliferation)
    print("Prediction interval: 112 days")
    print("Dice:", round(dice, 4))
    print(
        "Predicted volume:",
        round(predicted_volume, 2),
        "cm3",
    )
    print(
        "Observed t2 volume:",
        round(observed_volume, 2),
        "cm3",
    )
    print(
        "Volume error:",
        round(volume_error * 100, 2),
        "%",
    )
    print(
        "outside domain:",
        np.count_nonzero(
            concentration_t2[~domain]
        ),
    )
    print()
    print("Persistence baseline")
    print("--------------------")
    print("Dice:", round(persistence_dice, 4))
    print(
        "Predicted volume:",
        round(persistence_volume, 2),
        "cm3",
    )
    print(
        "Volume error:",
        round(persistence_volume_error * 100, 2),
        "%",
    )


if __name__ == "__main__":
    main()