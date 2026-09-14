import argparse
from pathlib import Path

import pandas as pd

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
    load_cohort_experiment_config,
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

DEFAULT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate predefined RT-aware "
            "calibration scenarios on t1->t2."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--patient",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--scenario",
        type=float,
        nargs=3,
        action="append",
        metavar=(
            "ALPHA",
            "D",
            "RHO",
        ),
        required=True,
        help=(
            "Calibration scenario: "
            "alpha D rho. May be repeated."
        ),
    )

    parser.add_argument(
        "--alpha-beta",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.alpha_beta <= 0:
        raise ValueError(
            "--alpha-beta must be positive"
        )

    experiment = (
        load_cohort_experiment_config(
            args.config
        )
    )

    metadata = CFBMetadata(
        experiment.metadata_root
    )

    treatment_metadata = (
        CFBTreatmentMetadata(
            experiment.metadata_root
        )
    )

    patient = metadata.patient(
        args.patient
    )

    t1 = load_patient_timepoint(
        experiment.patients_root,
        args.patient,
        patient.get_timepoint("t1"),
    )

    t2 = load_patient_timepoint(
        experiment.patients_root,
        args.patient,
        patient.get_timepoint("t2"),
    )

    t1_gtv = resample_volume(
        t1.gtv,
        experiment.evaluation.target_spacing,
        is_mask=True,
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
            "t1/t2 geometry mismatch"
        )

    if not same_geometry(
        t1_gtv,
        t1_brain,
    ):
        raise ValueError(
            "t1 GTV / brain geometry mismatch"
        )

    dt01 = patient.interval_days(
        "t0",
        "t1",
    )

    dt12 = patient.interval_days(
        "t1",
        "t2",
    )

    domain = build_computational_domain(
        t1_brain.data,
        t1_gtv.data,
    )

    initial = initial_condition_from_gtv(
        t1_gtv.data,
        domain,
        threshold=(
            experiment.evaluation.threshold
        ),
    )

    observed_t2 = (
        t2_gtv.data
        > experiment.evaluation.threshold
    )

    persistence = (
        t1_gtv.data
        > experiment.evaluation.threshold
    )

    treatment_record = (
        treatment_metadata.treatment(
            args.patient
        )
    )

    if treatment_record is None:
        raise ValueError(
            f"Patient {args.patient} has "
            "no treatment record"
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
            f"Patient {args.patient} has "
            "incomplete RT metadata"
        )

    schedule = (
        reconstruct_weekday_like_schedule(
            start_day=rt_start_day,
            total_dose_gy=total_dose_gy,
            fractions_number=(
                fractions_number
            ),
        )
    )

    rows: list[
        dict[str, object]
    ] = []

    persistence_dice = dice_score(
        persistence,
        observed_t2,
    )

    persistence_volume_error = (
        relative_volume_error(
            persistence,
            observed_t2,
        )
    )

    rows.append(
        {
            "patient_id": args.patient,
            "model": "persistence",
            "alpha_per_gy": None,
            "D": None,
            "rho": None,
            "dice": persistence_dice,
            "volume_error": (
                persistence_volume_error
            ),
        }
    )

    for scenario in args.scenario:
        alpha = scenario[0]
        diffusion = scenario[1]
        proliferation = scenario[2]

        if alpha < 0:
            raise ValueError(
                "Alpha must be non-negative"
            )

        if diffusion < 0:
            raise ValueError(
                "D must be non-negative"
            )

        if proliferation < 0:
            raise ValueError(
                "rho must be non-negative"
            )

        radiobiology = (
            RadiobiologyParameters(
                alpha_per_gy=alpha,
                alpha_beta_ratio_gy=(
                    args.alpha_beta
                ),
            )
        )

        treatment = (
            build_fractionated_radiotherapy(
                schedule,
                radiobiology,
            )
        )

        params = (
            ReactionDiffusionParameters(
                diffusion=diffusion,
                proliferation=proliferation,
            )
        )

        predicted_field = (
            simulate_reaction_diffusion(
                initial,
                params,
                spacing=t1_gtv.spacing,
                duration_days=float(dt12),
                dt=experiment.evaluation.dt,
                domain_mask=domain,
                treatment=treatment,
                start_time_day=float(dt01),
            )
        )

        predicted_mask = (
            predicted_field
            >= experiment.evaluation.threshold
        )

        dice = dice_score(
            predicted_mask,
            observed_t2,
        )

        volume_error = (
            relative_volume_error(
                predicted_mask,
                observed_t2,
            )
        )

        rows.append(
            {
                "patient_id": args.patient,
                "model": "fractionated_rt",
                "alpha_per_gy": alpha,
                "D": diffusion,
                "rho": proliferation,
                "dice": dice,
                "volume_error": (
                    volume_error
                ),
            }
        )

    dataframe = pd.DataFrame(
        rows
    )

    print()
    print("=" * 60)
    print("T1 -> T2 PREDICTION")
    print("=" * 60)

    print(
        dataframe.to_string(
            index=False,
            float_format=(
                lambda value: (
                    f"{value:.4f}"
                )
            ),
        )
    )

    print()
    print(
        f"t0 -> t1: {dt01} days"
    )

    print(
        f"t1 -> t2: {dt12} days"
    )

    print(
        "Last reconstructed RT fraction: "
        f"day {schedule.fraction_days[-1]:.1f}"
    )

    print(
        "Prediction starts at: "
        f"day {float(dt01):.1f}"
    )

    output_path = (
        args.output
        if args.output is not None
        else Path("results")
        / (
            f"patient_{args.patient}"
            "_rt_prediction.csv"
        )
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        output_path,
        index=False,
    )

    print()
    print(
        f"Saved: {output_path}"
    )


if __name__ == "__main__":
    main()