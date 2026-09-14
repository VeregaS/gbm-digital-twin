import argparse
from pathlib import Path

import pandas as pd

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
    load_cohort_experiment_config,
)
from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.reaction_diffusion import (
    build_computational_domain,
    initial_condition_from_gtv,
)
from gbm_twin.models.rt_schedule import (
    build_fractionated_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.preprocessing.resampling import (
    resample_volume,
)

DEFAULT_CONFIG = Path(
    "configs/experiments/mini_cohort.yaml"
)

DEFAULT_CACHE_DIR = Path(
    ".cache/gbm_twin/calibration"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run adaptive treatment-aware "
            "t0->t1 calibration."
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
        default=25,
    )

    parser.add_argument(
        "--alpha",
        type=float,
        default=0.10,
    )

    parser.add_argument(
        "--alpha-beta",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.alpha < 0:
        raise ValueError(
            "--alpha must be non-negative"
        )

    if args.alpha_beta <= 0:
        raise ValueError(
            "--alpha-beta must be positive"
        )

    if args.workers < 1:
        raise ValueError(
            "--workers must be at least 1"
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

    t0 = load_patient_timepoint(
        experiment.patients_root,
        args.patient,
        patient.get_timepoint("t0"),
    )

    t1 = load_patient_timepoint(
        experiment.patients_root,
        args.patient,
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
            "t0/t1 geometry mismatch"
        )

    if not same_geometry(
        t0_gtv,
        t0_brain,
    ):
        raise ValueError(
            "t0 GTV / brain geometry mismatch"
        )

    dt01 = patient.interval_days(
        "t0",
        "t1",
    )

    domain = build_computational_domain(
        t0_brain.data,
        t0_gtv.data,
    )

    initial = initial_condition_from_gtv(
        t0_gtv.data,
        domain,
        threshold=(
            experiment.evaluation.threshold
        ),
    )

    observed_t1 = (
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
            f"Patient {args.patient} "
            "has no treatment record"
        )

    if (
        treatment_record.radiotherapy_start_day
        is None
        or treatment_record.dose_gy
        is None
        or treatment_record.fractions_number
        is None
    ):
        raise ValueError(
            f"Patient {args.patient} "
            "has incomplete RT metadata"
        )

    schedule = (
        reconstruct_weekday_like_schedule(
            start_day=(
                treatment_record
                .radiotherapy_start_day
            ),
            total_dose_gy=(
                treatment_record.dose_gy
            ),
            fractions_number=(
                treatment_record
                .fractions_number
            ),
        )
    )

    radiobiology = (
        RadiobiologyParameters(
            alpha_per_gy=args.alpha,
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

    print()
    print("=" * 60)
    print("ADAPTIVE RT CALIBRATION")
    print("=" * 60)

    print(
        f"Patient: {args.patient}"
    )

    print(
        f"alpha: {args.alpha:.4f} /Gy"
    )

    print(
        f"workers: {args.workers}"
    )

    result = adaptive_grid_search(
        initial,
        observed_t1,
        domain,
        spacing=t0_gtv.spacing,
        duration_days=float(dt01),
        dt=experiment.evaluation.dt,
        diffusion_values=list(
            experiment.evaluation.diffusion_values
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
            experiment.evaluation.volume_weight
        ),
        treatment=treatment,
        start_time_day=0.0,
        cache_dir=DEFAULT_CACHE_DIR,
        workers=args.workers,
    )

    best = result.best

    dataframe = pd.DataFrame(
        [
            {
                "patient_id": args.patient,
                "alpha_per_gy": args.alpha,
                "D": best.diffusion,
                "rho": best.proliferation,
                "dice": best.dice,
                "volume_error": (
                    best.volume_error
                ),
                "loss": best.loss,
                "coarse_D": (
                    result
                    .coarse_best
                    .diffusion
                ),
                "coarse_rho": (
                    result
                    .coarse_best
                    .proliferation
                ),
            }
        ]
    )

    print()
    print("=" * 60)
    print("ADAPTIVE CALIBRATION RESULT")
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
        "Refined D grid: "
        f"{result.refined_diffusion_values}"
    )

    print(
        "Refined rho grid: "
        f"{result.refined_proliferation_values}"
    )

    output_path = (
        args.output
        if args.output is not None
        else Path("results")
        / (
            f"patient_{args.patient}"
            "_adaptive_rt_calibration.csv"
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