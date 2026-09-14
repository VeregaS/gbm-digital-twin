import argparse
import math
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
from gbm_twin.models.treatment import (
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
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
            "Compare RT-only calibration against "
            "RT with a fixed decaying post-RT effect."
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
        "--kappa0",
        type=float,
        default=0.03,
        help="Initial post-RT kill rate in 1/day.",
    )

    parser.add_argument(
        "--tau",
        type=float,
        default=30.0,
        help="Post-RT decay time in days.",
    )

    parser.add_argument(
        "--diffusion",
        type=float,
        nargs="+",
        default=None,
    )

    parser.add_argument(
        "--rho",
        type=float,
        nargs="+",
        default=None,
    )

    parser.add_argument(
        "--memory-only",
        action="store_true",
        help="Skip RT-only calibration.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help=(
            "Number of parallel PDE workers. "
            "Default: 2."
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
    alpha: float,
    beta: float,
    survival_per_fraction: float,
    kappa0: float | None,
    tau: float | None,
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
        "post_rt_kappa0_per_day": kappa0,
        "post_rt_tau_days": tau,
        "D": result.diffusion,
        "rho": result.proliferation,
        "dice": result.dice,
        "volume_error": result.volume_error,
        "loss": result.loss,
    }


def run_calibration(
    *,
    label: str,
    initial_field,
    observed_mask,
    domain_mask,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    diffusion_values: list[float],
    proliferation_values: list[float],
    threshold: float,
    volume_weight: float,
    treatment,
    workers: int,
) -> CalibrationResult:
    print()
    print("=" * 60)
    print(label)
    print("=" * 60)

    results = grid_search(
        initial_field,
        observed_mask,
        domain_mask,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
        diffusion_values=diffusion_values,
        proliferation_values=(
            proliferation_values
        ),
        threshold=threshold,
        volume_weight=volume_weight,
        treatment=treatment,
        start_time_day=0.0,
        cache_dir=DEFAULT_CACHE_DIR,
        workers=workers,
    )

    return results[0]


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

    if args.kappa0 < 0:
        raise ValueError(
            "--kappa0 must be non-negative"
        )

    if args.tau <= 0:
        raise ValueError(
            "--tau must be positive"
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

    diffusion_values = (
        list(args.diffusion)
        if args.diffusion is not None
        else list(
            experiment.evaluation.diffusion_values
        )
    )

    proliferation_values = (
        list(args.rho)
        if args.rho is not None
        else list(
            experiment.evaluation.proliferation_values
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
        treatment_record.radiotherapy_start_day
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
            fractions_number=fractions_number,
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

    fractionated_rt = (
        build_fractionated_radiotherapy(
            schedule,
            radiobiology,
        )
    )

    last_fraction_day = (
        schedule.fraction_days[-1]
    )

    post_effect = PostRadiotherapyEffect(
        start_day=last_fraction_day,
        initial_kill_rate=args.kappa0,
        decay_time_days=args.tau,
    )

    rt_with_memory = RadiotherapyProtocol(
        fractions=fractionated_rt,
        post_effect=post_effect,
    )

    post_rt_gap_days = (
        float(dt01)
        - last_fraction_day
    )

    if post_rt_gap_days < 0:
        raise ValueError(
            "t1 occurs before reconstructed "
            "RT completion"
        )

    cumulative_post_rt_kill = (
        args.kappa0
        * args.tau
        * (
            1.0
            - math.exp(
                -post_rt_gap_days
                / args.tau
            )
        )
    )

    print()
    print("=" * 60)
    print("CALIBRATION SETUP")
    print("=" * 60)

    print(
        f"Patient: {args.patient}"
    )

    print(
        f"D grid: {diffusion_values}"
    )

    print(
        f"rho grid: {proliferation_values}"
    )

    print(
        f"alpha: {args.alpha:.4f} /Gy"
    )

    print(
        f"alpha/beta: "
        f"{args.alpha_beta:.2f} Gy"
    )

    print(
        f"kappa0: "
        f"{args.kappa0:.4f} /day"
    )

    print(
        f"tau: {args.tau:.1f} days"
    )

    print(
        f"workers: {args.workers}"
    )

    print(
        f"t0 -> t1: {dt01} days"
    )

    print(
        f"RT last fraction: "
        f"day {last_fraction_day:.1f}"
    )

    print(
        f"Post-RT gap to t1: "
        f"{post_rt_gap_days:.1f} days"
    )

    print(
        "Integrated post-RT kill to t1: "
        f"{cumulative_post_rt_kill:.4f}"
    )

    rt_only_best: (
        CalibrationResult
        | None
    ) = None

    if not args.memory_only:
        rt_only_best = run_calibration(
            label=(
                f"PATIENT {args.patient}: "
                "FRACTIONATED RT"
            ),
            initial_field=initial,
            observed_mask=observed_t1,
            domain_mask=domain,
            spacing=t0_gtv.spacing,
            duration_days=float(dt01),
            dt=experiment.evaluation.dt,
            diffusion_values=diffusion_values,
            proliferation_values=(
                proliferation_values
            ),
            threshold=(
                experiment.evaluation.threshold
            ),
            volume_weight=(
                experiment.evaluation.volume_weight
            ),
            treatment=fractionated_rt,
            workers=args.workers,
        )

    rt_memory_best = run_calibration(
        label=(
            f"PATIENT {args.patient}: "
            "RT + POST-RT EFFECT"
        ),
        initial_field=initial,
        observed_mask=observed_t1,
        domain_mask=domain,
        spacing=t0_gtv.spacing,
        duration_days=float(dt01),
        dt=experiment.evaluation.dt,
        diffusion_values=diffusion_values,
        proliferation_values=(
            proliferation_values
        ),
        threshold=(
            experiment.evaluation.threshold
        ),
        volume_weight=(
            experiment.evaluation.volume_weight
        ),
        treatment=rt_with_memory,
        workers=args.workers,
    )

    rows: list[
        dict[str, object]
    ] = []

    if rt_only_best is not None:
        rows.append(
            result_row(
                patient_id=args.patient,
                model="fractionated_rt",
                alpha=(
                    radiobiology.alpha_per_gy
                ),
                beta=(
                    radiobiology.beta_per_gy2
                ),
                survival_per_fraction=(
                    fractionated_rt
                    .survival_fraction_per_fraction
                ),
                kappa0=None,
                tau=None,
                result=rt_only_best,
            )
        )

    rows.append(
        result_row(
            patient_id=args.patient,
            model=(
                "fractionated_rt_post_effect"
            ),
            alpha=(
                radiobiology.alpha_per_gy
            ),
            beta=(
                radiobiology.beta_per_gy2
            ),
            survival_per_fraction=(
                fractionated_rt
                .survival_fraction_per_fraction
            ),
            kappa0=args.kappa0,
            tau=args.tau,
            result=rt_memory_best,
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
        f"{last_fraction_day:.1f}"
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
            "_post_rt_calibration.csv"
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