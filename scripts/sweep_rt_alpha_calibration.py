import argparse
from pathlib import Path
from typing import Any

import numpy as np
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

DEFAULT_CACHE_DIR = Path(
    ".cache/gbm_twin/calibration"
)

DEFAULT_OUTPUT = Path(
    "results/rt_alpha_sweep_soft.csv"
)

DEFAULT_SUMMARY_OUTPUT = Path(
    "results/rt_alpha_sweep_soft_summary.csv"
)

DEFAULT_PATIENTS = [
    8,
    25,
    65,
    99,
    108,
    112,
    214,
    251,
]

DEFAULT_ALPHAS = [
    0.01,
    0.025,
    0.05,
    0.075,
    0.10,
]

ResultRow = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep global effective RT alpha using "
            "t0-to-t1 calibration only."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--patients",
        type=int,
        nargs="+",
        default=DEFAULT_PATIENTS,
    )

    parser.add_argument(
        "--alpha",
        type=float,
        nargs="+",
        default=DEFAULT_ALPHAS,
    )

    parser.add_argument(
        "--alpha-beta",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--soft-temperature",
        type=float,
        default=0.05,
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT,
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    return parser.parse_args()


def dataframe_rows(
    dataframe: pd.DataFrame,
) -> list[ResultRow]:
    records = dataframe.to_dict(
        orient="records"
    )

    return [
        {
            str(key): value
            for key, value in record.items()
        }
        for record in records
    ]


def result_key(
    row: ResultRow,
) -> tuple[int, float]:
    return (
        int(row["patient_id"]),
        round(
            float(row["alpha_per_gy"]),
            12,
        ),
    )


def save_detail(
    rows: list[ResultRow],
    output: Path,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = pd.DataFrame(
        rows
    )

    dataframe = dataframe.sort_values(
        [
            "patient_id",
            "alpha_per_gy",
        ]
    ).reset_index(
        drop=True
    )

    dataframe.to_csv(
        output,
        index=False,
    )


def create_summary(
    detail: pd.DataFrame,
) -> pd.DataFrame:
    summary = (
        detail.groupby(
            "alpha_per_gy",
            as_index=False,
        )
        .agg(
            patients=(
                "patient_id",
                "count",
            ),
            mean_calibration_loss=(
                "calibration_loss",
                "mean",
            ),
            median_calibration_loss=(
                "calibration_loss",
                "median",
            ),
            mean_soft_dice=(
                "calibration_dice",
                "mean",
            ),
            mean_hard_t1_dice=(
                "hard_t1_dice",
                "mean",
            ),
            hard_empty_count=(
                "hard_empty_t1",
                "sum",
            ),
            diffusion_zero_count=(
                "diffusion_zero",
                "sum",
            ),
            rho_upper_count=(
                "rho_at_refined_upper",
                "sum",
            ),
            mean_max_c=(
                "max_c_t1",
                "mean",
            ),
        )
    )

    return summary.sort_values(
        [
            "mean_calibration_loss",
            "hard_empty_count",
        ]
    ).reset_index(
        drop=True
    )


def main() -> None:
    args = parse_args()

    if args.alpha_beta <= 0:
        raise ValueError(
            "--alpha-beta must be positive"
        )

    if args.soft_temperature <= 0:
        raise ValueError(
            "--soft-temperature must be positive"
        )

    if args.workers < 1:
        raise ValueError(
            "--workers must be at least 1"
        )

    if any(
        alpha <= 0
        for alpha in args.alpha
    ):
        raise ValueError(
            "All alpha values must be positive"
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

    rows: list[ResultRow] = []

    completed: set[
        tuple[int, float]
    ] = set()

    if (
        args.output.exists()
        and not args.force
    ):
        existing = pd.read_csv(
            args.output
        )

        rows = dataframe_rows(
            existing
        )

        completed = {
            result_key(row)
            for row in rows
        }

    print()
    print("=" * 72)
    print(
        "GLOBAL RT ALPHA SWEEP — T0 -> T1 ONLY"
    )
    print("=" * 72)

    print(
        f"Patients: {args.patients}"
    )

    print(
        f"Alpha values: {args.alpha}"
    )

    print(
        "Calibration objective: soft"
    )

    print(
        "Soft temperature: "
        f"{args.soft_temperature:.4f}"
    )

    print(
        f"Workers: {args.workers}"
    )

    for patient_id in args.patients:
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

        # Deliberately no t2 loading here.

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

        threshold = (
            experiment
            .evaluation
            .threshold
        )

        domain = (
            build_computational_domain(
                t0_brain.data,
                t0_gtv.data,
            )
        )

        initial = (
            initial_condition_from_gtv(
                t0_gtv.data,
                domain,
                threshold=threshold,
            )
        ).astype(
            np.float32,
            copy=False,
        )

        observed_t1 = (
            t1_gtv.data
            > threshold
        )

        dt01 = patient.interval_days(
            "t0",
            "t1",
        )

        treatment_record = (
            treatment_metadata.treatment(
                patient_id
            )
        )

        if treatment_record is None:
            raise ValueError(
                f"Patient {patient_id}: "
                "missing RT metadata"
            )

        rt_start_day = (
            treatment_record
            .radiotherapy_start_day
        )

        total_dose = (
            treatment_record
            .dose_gy
        )

        fractions = (
            treatment_record
            .fractions_number
        )

        if (
            rt_start_day is None
            or total_dose is None
            or fractions is None
        ):
            raise ValueError(
                f"Patient {patient_id}: "
                "incomplete RT metadata"
            )

        schedule = (
            reconstruct_weekday_like_schedule(
                start_day=rt_start_day,
                total_dose_gy=total_dose,
                fractions_number=fractions,
            )
        )

        print()
        print("=" * 72)

        print(
            f"PATIENT {patient_id}"
        )

        print("=" * 72)

        for alpha in args.alpha:
            key = (
                patient_id,
                round(
                    alpha,
                    12,
                ),
            )

            if (
                key in completed
                and not args.force
            ):
                print(
                    f"alpha={alpha:.4f}: "
                    "already evaluated, skipping"
                )

                continue

            print()
            print(
                f"alpha={alpha:.4f} /Gy"
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

            calibration = (
                adaptive_grid_search(
                    initial,
                    observed_t1,
                    domain,
                    spacing=t0_gtv.spacing,
                    duration_days=float(
                        dt01
                    ),
                    dt=(
                        experiment
                        .evaluation
                        .dt
                    ),
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
                    threshold=threshold,
                    volume_weight=(
                        experiment
                        .evaluation
                        .volume_weight
                    ),
                    treatment=treatment,
                    start_time_day=0.0,
                    cache_dir=(
                        DEFAULT_CACHE_DIR
                    ),
                    workers=args.workers,
                    objective="soft",
                    soft_temperature=(
                        args.soft_temperature
                    ),
                )
            )

            best = calibration.best

            params = (
                ReactionDiffusionParameters(
                    diffusion=best.diffusion,
                    proliferation=(
                        best.proliferation
                    ),
                )
            )

            predicted_field = (
                simulate_reaction_diffusion(
                    initial,
                    params,
                    spacing=t0_gtv.spacing,
                    duration_days=float(
                        dt01
                    ),
                    dt=(
                        experiment
                        .evaluation
                        .dt
                    ),
                    domain_mask=domain,
                    treatment=treatment,
                    start_time_day=0.0,
                )
            )

            predicted_hard = (
                predicted_field
                >= threshold
            )

            hard_dice = dice_score(
                predicted_hard,
                observed_t1,
            )

            hard_volume_error = (
                relative_volume_error(
                    predicted_hard,
                    observed_t1,
                )
            )

            hard_empty = (
                np.count_nonzero(
                    predicted_hard
                )
                == 0
            )

            diffusion_zero = bool(
                np.isclose(
                    best.diffusion,
                    0.0,
                )
            )

            rho_at_upper = bool(
                np.isclose(
                    best.proliferation,
                    max(
                        calibration
                        .refined_proliferation_values
                    ),
                )
            )

            dose_per_fraction = (
                total_dose
                / fractions
            )

            beta = (
                alpha
                / args.alpha_beta
            )

            fraction_survival = float(
                np.exp(
                    -(
                        alpha
                        * dose_per_fraction
                        + beta
                        * dose_per_fraction**2
                    )
                )
            )

            cumulative_survival = (
                fraction_survival
                ** fractions
            )

            result_row: ResultRow = {
                "patient_id": patient_id,
                "alpha_per_gy": alpha,
                "alpha_beta_ratio_gy": (
                    args.alpha_beta
                ),
                "soft_temperature": (
                    args.soft_temperature
                ),
                "dt01": dt01,
                "rt_total_dose_gy": (
                    total_dose
                ),
                "rt_fractions": fractions,
                "cumulative_rt_survival": (
                    cumulative_survival
                ),
                "diffusion": (
                    best.diffusion
                ),
                "proliferation": (
                    best.proliferation
                ),
                "calibration_dice": (
                    best.dice
                ),
                "calibration_volume_error": (
                    best.volume_error
                ),
                "calibration_loss": (
                    best.loss
                ),
                "hard_t1_dice": (
                    hard_dice
                ),
                "hard_t1_volume_error": (
                    hard_volume_error
                ),
                "hard_empty_t1": (
                    hard_empty
                ),
                "max_c_t1": float(
                    np.max(
                        predicted_field
                    )
                ),
                "diffusion_zero": (
                    diffusion_zero
                ),
                "rho_at_refined_upper": (
                    rho_at_upper
                ),
            }

            rows = [
                row
                for row in rows
                if result_key(row)
                != key
            ]

            rows.append(
                result_row
            )

            completed.add(
                key
            )

            save_detail(
                rows,
                args.output,
            )

            print(
                "Best: "
                f"D={best.diffusion:.4f}, "
                f"rho={best.proliferation:.4f}, "
                f"loss={best.loss:.4f}"
            )

            print(
                "Hard t1: "
                f"Dice={hard_dice:.4f}, "
                f"empty={hard_empty}, "
                f"max(c)={np.max(predicted_field):.4f}"
            )

    detail = pd.DataFrame(
        rows
    )

    summary = create_summary(
        detail
    )

    args.summary_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary.to_csv(
        args.summary_output,
        index=False,
    )

    print()
    print("=" * 72)
    print(
        "GLOBAL ALPHA SUMMARY"
    )
    print("=" * 72)

    columns = [
        "alpha_per_gy",
        "mean_calibration_loss",
        "mean_soft_dice",
        "mean_hard_t1_dice",
        "hard_empty_count",
        "diffusion_zero_count",
        "rho_upper_count",
    ]

    print(
        summary[
            columns
        ].to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.4f}"
            ),
        )
    )

    print()
    print(
        f"Detail saved: {args.output}"
    )

    print(
        "Summary saved: "
        f"{args.summary_output}"
    )


if __name__ == "__main__":
    main()