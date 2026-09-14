import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from gbm_twin.data.cfb_metadata import (
    CFBMetadata,
)
from gbm_twin.data.cfb_treatment import (
    CFBTreatmentMetadata,
)
from gbm_twin.data.patient_loader import (
    load_patient_timepoint,
)
from gbm_twin.evaluation.config import (
    load_cohort_experiment_config,
)
from gbm_twin.evaluation.soft_metrics import (
    soft_threshold_membership,
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

DEFAULT_CALIBRATION = Path(
    "results/mini_cohort_treatment_aware_soft.csv"
)

DEFAULT_OUTPUT = Path(
    "results/rt_calibration_failure_diagnostics.csv"
)

DEFAULT_PATIENTS = [
    108,
    112,
    214,
    251,
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose treatment-aware calibration "
            "failure after reconstructed RT."
        )
    )

    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
    )

    parser.add_argument(
        "--calibration",
        type=Path,
        default=DEFAULT_CALIBRATION,
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
        default=0.10,
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
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def volume_cm3(
    voxel_count: float,
    spacing: tuple[float, float, float],
) -> float:
    voxel_volume_mm3 = float(
        np.prod(
            np.asarray(
                spacing,
                dtype=np.float64,
            )
        )
    )

    return (
        voxel_count
        * voxel_volume_mm3
        / 1000.0
    )


def field_metrics(
    field: np.ndarray,
    *,
    domain: np.ndarray,
    spacing: tuple[float, float, float],
    threshold: float,
    soft_temperature: float,
) -> dict[str, float]:
    hard_mask = (
        field >= threshold
    )

    membership = (
        soft_threshold_membership(
            field,
            threshold=threshold,
            temperature=soft_temperature,
            domain_mask=domain,
        )
    )

    hard_voxels = float(
        np.count_nonzero(
            hard_mask
        )
    )

    soft_voxels = float(
        np.sum(
            membership,
            dtype=np.float64,
        )
    )

    return {
        "max_c": float(
            np.max(field)
        ),
        "mean_c_active": float(
            np.mean(
                field[domain]
            )
        ),
        "mass": float(
            np.sum(
                field,
                dtype=np.float64,
            )
        ),
        "hard_volume_cm3": volume_cm3(
            hard_voxels,
            spacing,
        ),
        "soft_volume_cm3": volume_cm3(
            soft_voxels,
            spacing,
        ),
    }


def main() -> None:
    args = parse_args()

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

    calibration = pd.read_csv(
        args.calibration
    )

    threshold = (
        experiment.evaluation.threshold
    )

    rows: list[
        dict[str, float | int]
    ] = []

    print()
    print("=" * 72)
    print(
        "RT CALIBRATION FAILURE DIAGNOSTICS"
    )
    print("=" * 72)

    for patient_id in args.patients:
        patient_rows = calibration[
            calibration["patient_id"]
            == patient_id
        ]

        if patient_rows.empty:
            raise ValueError(
                f"Patient {patient_id} "
                "not found in calibration CSV"
            )

        row = patient_rows.iloc[0]

        diffusion = float(
            row["diffusion"]
        )

        proliferation = float(
            row["proliferation"]
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

        observed_t1_volume = (
            volume_cm3(
                float(
                    np.count_nonzero(
                        observed_t1
                    )
                ),
                t1_gtv.spacing,
            )
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

        start_day = (
            treatment_record
            .radiotherapy_start_day
        )

        total_dose = (
            treatment_record.dose_gy
        )

        fractions = (
            treatment_record
            .fractions_number
        )

        if (
            start_day is None
            or total_dose is None
            or fractions is None
        ):
            raise ValueError(
                f"Patient {patient_id}: "
                "incomplete RT metadata"
            )

        schedule = (
            reconstruct_weekday_like_schedule(
                start_day=start_day,
                total_dose_gy=total_dose,
                fractions_number=fractions,
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

        params = (
            ReactionDiffusionParameters(
                diffusion=diffusion,
                proliferation=proliferation,
            )
        )

        dt01 = patient.interval_days(
            "t0",
            "t1",
        )

        with_rt = (
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

        without_rt = (
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
                treatment=None,
                start_time_day=0.0,
            )
        )

        rt_metrics = field_metrics(
            with_rt,
            domain=domain,
            spacing=t0_gtv.spacing,
            threshold=threshold,
            soft_temperature=(
                args.soft_temperature
            ),
        )

        no_rt_metrics = field_metrics(
            without_rt,
            domain=domain,
            spacing=t0_gtv.spacing,
            threshold=threshold,
            soft_temperature=(
                args.soft_temperature
            ),
        )

        dose_per_fraction = (
            total_dose
            / fractions
        )

        beta = (
            args.alpha
            / args.alpha_beta
        )

        survival_per_fraction = float(
            np.exp(
                -(
                    args.alpha
                    * dose_per_fraction
                    + beta
                    * dose_per_fraction**2
                )
            )
        )

        cumulative_survival = (
            survival_per_fraction
            ** fractions
        )

        last_fraction_day = float(
            schedule.fraction_days[-1]
        )

        post_rt_gap = (
            float(dt01)
            - last_fraction_day
        )

        print()
        print("-" * 72)

        print(
            f"PATIENT {patient_id}"
        )

        print(
            f"D={diffusion:.4f}, "
            f"rho={proliferation:.4f}"
        )

        print(
            "RT: "
            f"{total_dose:.2f} Gy / "
            f"{fractions} fractions"
        )

        print(
            "Fraction survival: "
            f"{survival_per_fraction:.6f}"
        )

        print(
            "Cumulative RT survival: "
            f"{cumulative_survival:.8f}"
        )

        print(
            "Post-RT gap to t1: "
            f"{post_rt_gap:.1f} days"
        )

        print(
            "Observed t1 volume: "
            f"{observed_t1_volume:.3f} cm3"
        )

        print()
        print("WITH RT")

        print(
            "  max(c): "
            f"{rt_metrics['max_c']:.6f}"
        )

        print(
            "  mass: "
            f"{rt_metrics['mass']:.3f}"
        )

        print(
            "  hard volume: "
            f"{rt_metrics['hard_volume_cm3']:.3f} cm3"
        )

        print(
            "  soft volume: "
            f"{rt_metrics['soft_volume_cm3']:.3f} cm3"
        )

        print()
        print("WITHOUT RT")

        print(
            "  max(c): "
            f"{no_rt_metrics['max_c']:.6f}"
        )

        print(
            "  mass: "
            f"{no_rt_metrics['mass']:.3f}"
        )

        print(
            "  hard volume: "
            f"{no_rt_metrics['hard_volume_cm3']:.3f} cm3"
        )

        print(
            "  soft volume: "
            f"{no_rt_metrics['soft_volume_cm3']:.3f} cm3"
        )

        rows.append(
            {
                "patient_id": patient_id,
                "diffusion": diffusion,
                "proliferation": proliferation,
                "dt01": dt01,
                "rt_total_dose_gy": (
                    total_dose
                ),
                "rt_fractions": fractions,
                "rt_dose_per_fraction_gy": (
                    dose_per_fraction
                ),
                "rt_last_fraction_day": (
                    last_fraction_day
                ),
                "post_rt_gap_days": (
                    post_rt_gap
                ),
                "survival_per_fraction": (
                    survival_per_fraction
                ),
                "cumulative_rt_survival": (
                    cumulative_survival
                ),
                "observed_t1_volume_cm3": (
                    observed_t1_volume
                ),
                "rt_max_c": (
                    rt_metrics["max_c"]
                ),
                "rt_mass": (
                    rt_metrics["mass"]
                ),
                "rt_hard_volume_cm3": (
                    rt_metrics[
                        "hard_volume_cm3"
                    ]
                ),
                "rt_soft_volume_cm3": (
                    rt_metrics[
                        "soft_volume_cm3"
                    ]
                ),
                "no_rt_max_c": (
                    no_rt_metrics["max_c"]
                ),
                "no_rt_mass": (
                    no_rt_metrics["mass"]
                ),
                "no_rt_hard_volume_cm3": (
                    no_rt_metrics[
                        "hard_volume_cm3"
                    ]
                ),
                "no_rt_soft_volume_cm3": (
                    no_rt_metrics[
                        "soft_volume_cm3"
                    ]
                ),
            }
        )

    result = pd.DataFrame(
        rows
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        args.output,
        index=False,
    )

    print()
    print("=" * 72)

    print(
        f"Saved: {args.output}"
    )


if __name__ == "__main__":
    main()