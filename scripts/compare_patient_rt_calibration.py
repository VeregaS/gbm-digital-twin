import argparse
from pathlib import Path

import pandas as pd

from gbm_twin.calibration.grid_search import (
    CalibrationResult,
    grid_search,
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare untreated and RT-aware "
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
        default=8,
    )

    parser.add_argument(
        "--alpha",
        type=float,
        nargs="+",
        default=[
            0.02,
            0.05,
            0.10,
            0.15,
        ],
    )

    parser.add_argument(
        "--alpha-beta",
        type=float,
        default=10.0,
    )

    parser.add_argument(
        "--diffusion",
        type=float,
        nargs="+",
        default=None,
        help=(
            "Override diffusion grid. "
            "Defaults to experiment YAML."
        ),
    )

    parser.add_argument(
        "--rho",
        type=float,
        nargs="+",
        default=None,
        help=(
            "Override proliferation grid. "
            "Defaults to experiment YAML."
        ),
    )

    parser.add_argument(
        "--rt-only",
        action="store_true",
        help=(
            "Skip untreated calibration. "
            "Useful for local RT refinement."
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    return parser.parse_args()


def result_row(
    *,
    patient_id: int,
    model: str,
    alpha: float | None,
    beta: float | None,
    survival_per_fraction: float | None,
    result: CalibrationResult,
) -> dict[str, object]:
    return {
        "patient_id": patient_id,
        "model": model,
        "alpha_per_gy": alpha,
        "beta_per_gy2": beta,
        "survival_per_fraction": (
            survival_per_fraction
        ),
        "D": result.diffusion,
        "rho": result.proliferation,
        "dice": result.dice,
        "volume_error": result.volume_error,
        "loss": result.loss,
    }


def main() -> None:
    args = parse_args()

    if any(
        alpha < 0
        for alpha in args.alpha
    ):
        raise ValueError(
            "All alpha values must be non-negative"
        )

    if args.alpha_beta <= 0:
        raise ValueError(
            "--alpha-beta must be positive"
        )

    experiment = (
        load_cohort_experiment_config(
            args.config
        )
    )

    diffusion_values = (
        list(args.diffusion)
        if args.diffusion is not None
        else list(
            experiment
            .evaluation
            .diffusion_values
        )
    )

    proliferation_values = (
        list(args.rho)
        if args.rho is not None
        else list(
            experiment
            .evaluation
            .proliferation_values
        )
    )

    if not diffusion_values:
        raise ValueError(
            "Diffusion grid must not be empty"
        )

    if not proliferation_values:
        raise ValueError(
            "Rho grid must not be empty"
        )

    if any(
        value < 0
        for value in diffusion_values
    ):
        raise ValueError(
            "Diffusion values must be non-negative"
        )

    if any(
        value < 0
        for value in proliferation_values
    ):
        raise ValueError(
            "Rho values must be non-negative"
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

    print()
    print("=" * 60)
    print("CALIBRATION GRID")
    print("=" * 60)

    print(
        "D:",
        diffusion_values,
    )

    print(
        "rho:",
        proliferation_values,
    )

    print(
        "alpha:",
        args.alpha,
    )

    if not args.rt_only:
        print()
        print("=" * 60)
        print(
            f"PATIENT {args.patient}: UNTREATED"
        )
        print("=" * 60)

        untreated_results = grid_search(
            initial,
            observed_t1,
            domain,
            spacing=t0_gtv.spacing,
            duration_days=float(dt01),
            dt=experiment.evaluation.dt,
            diffusion_values=(
                diffusion_values
            ),
            proliferation_values=(
                proliferation_values
            ),
            threshold=(
                experiment
                .evaluation
                .threshold
            ),
            volume_weight=(
                experiment
                .evaluation
                .volume_weight
            ),
        )

        untreated_best = (
            untreated_results[0]
        )

        rows.append(
            result_row(
                patient_id=args.patient,
                model="untreated",
                alpha=None,
                beta=None,
                survival_per_fraction=None,
                result=untreated_best,
            )
        )

    for alpha in args.alpha:
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

        print()
        print("=" * 60)
        print(
            f"PATIENT {args.patient}: "
            f"RT alpha={alpha:.4f}"
        )
        print("=" * 60)

        results = grid_search(
            initial,
            observed_t1,
            domain,
            spacing=t0_gtv.spacing,
            duration_days=float(dt01),
            dt=experiment.evaluation.dt,
            diffusion_values=(
                diffusion_values
            ),
            proliferation_values=(
                proliferation_values
            ),
            threshold=(
                experiment
                .evaluation
                .threshold
            ),
            volume_weight=(
                experiment
                .evaluation
                .volume_weight
            ),
            treatment=treatment,
            start_time_day=0.0,
        )

        best = results[0]

        rows.append(
            result_row(
                patient_id=args.patient,
                model="fractionated_rt",
                alpha=(
                    radiobiology
                    .alpha_per_gy
                ),
                beta=(
                    radiobiology
                    .beta_per_gy2
                ),
                survival_per_fraction=(
                    treatment
                    .survival_fraction_per_fraction
                ),
                result=best,
            )
        )

    dataframe = pd.DataFrame(
        rows
    )

    print()
    print("=" * 60)
    print("CALIBRATION COMPARISON")
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
        f"Calibration interval: "
        f"{dt01} days"
    )

    print(
        f"RT reconstructed: "
        f"{schedule.total_dose_gy:.2f} Gy / "
        f"{schedule.fractions_number} fractions"
    )

    print(
        f"RT start day: "
        f"{schedule.start_day:.1f}"
    )

    print(
        f"RT last fraction day: "
        f"{schedule.fraction_days[-1]:.1f}"
    )

    print(
        f"Schedule assumption: "
        f"{schedule.assumption}"
    )

    output_path = (
        args.output
        if args.output is not None
        else Path("results")
        / (
            f"patient_{args.patient}"
            "_rt_calibration.csv"
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