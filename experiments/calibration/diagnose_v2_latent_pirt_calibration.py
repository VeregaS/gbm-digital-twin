from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from gbm_twin.calibration.grid_search import (
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
from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    build_computational_domain,
)
from gbm_twin.models.rt_schedule import (
    build_pirt_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.preprocessing.resampling import (
    resample_volume,
)

PATIENT_IDS = (
    8,
    25,
    65,
    99,
    108,
    112,
    214,
    251,
)

ALPHAS = [
    0.005,
    0.01,
    0.015,
]

DIFFUSION_VALUES = [
    0.0,
    0.005,
    0.015,
    0.030,
    0.045,
    0.060,
]

PROLIFERATION_VALUES = [
    0.0,
    0.015,
    0.035,
    0.055,
]

TARGET_SPACING = (
    2.0,
    2.0,
    2.0,
)

THRESHOLD = 0.5
SOFT_TEMPERATURE = 0.05
VOLUME_WEIGHT = 0.5
DT = 1.0

TRANSITION_WIDTH_MM = 4.0
ALPHA_BETA_RATIO_GY = 10.0


def dice_score(
    predicted: np.ndarray,
    observed: np.ndarray,
) -> float:
    predicted_mask = np.asarray(
        predicted,
        dtype=bool,
    )

    observed_mask = np.asarray(
        observed,
        dtype=bool,
    )

    intersection = np.count_nonzero(
        predicted_mask
        & observed_mask
    )

    denominator = (
        np.count_nonzero(
            predicted_mask
        )
        + np.count_nonzero(
            observed_mask
        )
    )

    if denominator == 0:
        return 1.0

    return (
        2.0
        * intersection
        / denominator
    )


def volume_cm3(
    mask: np.ndarray,
    *,
    spacing: tuple[
        float,
        float,
        float,
    ],
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
        np.count_nonzero(mask)
        * voxel_volume_mm3
        / 1000.0
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose continuous-latent + PIRT "
            "calibration using t0->t1 only."
        )
    )

    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=Path(
            r"D:\Datasets\CFB-GBM\metadata"
        ),
    )

    parser.add_argument(
        "--patients-root",
        type=Path,
        default=Path(
            r"D:\Datasets\CFB-GBM\patients"
        ),
    )

    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(
            ".cache/gbm_twin/calibration"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/"
            "v2_latent_pirt_alpha_expanded_d_8pt.csv"
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.workers <= 0:
        raise ValueError(
            "workers must be positive"
        )

    metadata = CFBMetadata(
        args.metadata_root
    )

    treatment_metadata = (
        CFBTreatmentMetadata(
            args.metadata_root
        )
    )

    rows: list[
        dict[str, float | int]
    ] = []

    print()
    print("=" * 78)
    print(
        "V2 CONTINUOUS LATENT + PIRT "
        "T0->T1 DIAGNOSTIC"
    )
    print("=" * 78)

    print(
        f"Patients: {list(PATIENT_IDS)}"
    )

    print(
        f"Alphas: {list(ALPHAS)}"
    )

    print(
        "Transition width: "
        f"{TRANSITION_WIDTH_MM:.2f} mm"
    )

    print(
        "IMPORTANT: t2 is not loaded "
        "or used by this experiment."
    )

    for patient_id in PATIENT_IDS:
        patient = metadata.patient(
            patient_id
        )

        t0_timepoint = (
            patient.get_timepoint(
                "t0"
            )
        )

        t1_timepoint = (
            patient.get_timepoint(
                "t1"
            )
        )

        dt01 = float(
            patient.interval_days(
                "t0",
                "t1",
            )
        )

        treatment_record = (
            treatment_metadata.treatment(
                patient_id
            )
        )

        if treatment_record is None:
            raise RuntimeError(
                f"Patient {patient_id}: "
                "missing treatment record"
            )

        rt_start_day = (
            treatment_record
            .radiotherapy_start_day
        )

        total_dose_gy = (
            treatment_record.dose_gy
        )

        fractions_number = (
            treatment_record
            .fractions_number
        )

        if (
            rt_start_day is None
            or total_dose_gy is None
            or fractions_number is None
        ):
            raise RuntimeError(
                f"Patient {patient_id}: "
                "RT schedule cannot be "
                "reconstructed"
            )

        t0_study = (
            load_patient_timepoint(
                args.patients_root,
                patient_id,
                t0_timepoint,
            )
        )

        t1_study = (
            load_patient_timepoint(
                args.patients_root,
                patient_id,
                t1_timepoint,
            )
        )

        t0_gtv = resample_volume(
            t0_study.gtv,
            TARGET_SPACING,
            is_mask=True,
        )

        t1_gtv = resample_volume(
            t1_study.gtv,
            TARGET_SPACING,
            is_mask=True,
        )

        t0_brain = resample_volume(
            t0_study.brain_mask,
            TARGET_SPACING,
            is_mask=True,
        )

        if not same_geometry(
            t0_gtv,
            t1_gtv,
        ):
            raise ValueError(
                f"Patient {patient_id}: "
                "t0/t1 GTV geometry mismatch"
            )

        if not same_geometry(
            t0_gtv,
            t0_brain,
        ):
            raise ValueError(
                f"Patient {patient_id}: "
                "t0 GTV/brain geometry mismatch"
            )

        t0_mask = (
            t0_gtv.data
            > THRESHOLD
        )

        observed_t1 = (
            t1_gtv.data
            > THRESHOLD
        )

        brain_mask = (
            t0_brain.data
            > THRESHOLD
        )

        domain = (
            build_computational_domain(
                brain_mask,
                t0_gtv.data,
                threshold=THRESHOLD,
            )
        )

        initial = (
            latent_state_from_gtv(
                t0_mask,
                brain_mask,
                spacing=t0_gtv.spacing,
                parameters=(
                    LatentStateParameters(
                        transition_width_mm=(
                            TRANSITION_WIDTH_MM
                        ),
                    )
                ),
            )
        )

        schedule = (
            reconstruct_weekday_like_schedule(
                start_day=rt_start_day,
                total_dose_gy=(
                    total_dose_gy
                ),
                fractions_number=(
                    fractions_number
                ),
            )
        )

        print()
        print("=" * 78)
        print(
            f"PATIENT {patient_id}"
        )
        print("=" * 78)

        print(
            f"dt01: {dt01:.1f} days"
        )

        print(
            "RT: "
            f"{total_dose_gy:.2f} Gy / "
            f"{fractions_number}"
        )

        print(
            "RT start: "
            f"{rt_start_day:.1f}"
        )

        print(
            "Initial max(c): "
            f"{np.max(initial):.6f}"
        )

        observed_t1_volume = volume_cm3(
            observed_t1,
            spacing=t0_gtv.spacing,
        )

        print(
            "Observed t1 volume: "
            f"{observed_t1_volume:.3f} cm3"
        )

        for alpha in ALPHAS:
            print()
            print("-" * 78)

            print(
                f"alpha={alpha:.3f} /Gy"
            )

            radiobiology = (
                RadiobiologyParameters(
                    alpha_per_gy=alpha,
                    alpha_beta_ratio_gy=(
                        ALPHA_BETA_RATIO_GY
                    ),
                )
            )

            pirt = (
                build_pirt_radiotherapy(
                    schedule,
                    radiobiology,
                )
            )

            results = grid_search(
                initial,
                observed_t1,
                domain,
                spacing=t0_gtv.spacing,
                duration_days=dt01,
                dt=DT,
                diffusion_values=(
                    DIFFUSION_VALUES
                ),
                proliferation_values=(
                    PROLIFERATION_VALUES
                ),
                threshold=THRESHOLD,
                volume_weight=(
                    VOLUME_WEIGHT
                ),
                treatment=pirt,
                start_time_day=0.0,
                cache_dir=args.cache_dir,
                workers=args.workers,
                objective="soft",
                soft_temperature=(
                    SOFT_TEMPERATURE
                ),
            )

            if not results:
                raise RuntimeError(
                    "Calibration returned "
                    "no candidates"
                )

            best = results[0]

            parameters = (
                ReactionDiffusionParameters(
                    diffusion=(
                        best.diffusion
                    ),
                    proliferation=(
                        best.proliferation
                    ),
                )
            )

            calibrated_field = (
                simulate_reaction_diffusion(
                    initial,
                    parameters,
                    spacing=t0_gtv.spacing,
                    duration_days=dt01,
                    dt=DT,
                    domain_mask=domain,
                    treatment=pirt,
                    start_time_day=0.0,
                )
            )

            hard_mask = (
                calibrated_field
                >= THRESHOLD
            )

            hard_dice = dice_score(
                hard_mask,
                observed_t1,
            )

            predicted_volume = (
                volume_cm3(
                    hard_mask,
                    spacing=t0_gtv.spacing,
                )
            )

            observed_volume = (
                volume_cm3(
                    observed_t1,
                    spacing=t0_gtv.spacing,
                )
            )

            hard_volume_error = (
                abs(
                    predicted_volume
                    - observed_volume
                )
                / observed_volume
                if observed_volume > 0
                else float("nan")
            )

            row = {
                "patient_id": (
                    patient_id
                ),
                "alpha_per_gy": (
                    alpha
                ),
                "dt01_days": (
                    dt01
                ),
                "rt_start_day": (
                    rt_start_day
                ),
                "rt_total_dose_gy": (
                    total_dose_gy
                ),
                "rt_fractions": (
                    fractions_number
                ),
                "transition_width_mm": (
                    TRANSITION_WIDTH_MM
                ),
                "diffusion": (
                    best.diffusion
                ),
                "proliferation": (
                    best.proliferation
                ),
                "soft_dice": (
                    best.dice
                ),
                "calibration_loss": (
                    best.loss
                ),
                "hard_t1_dice": (
                    hard_dice
                ),
                "hard_volume_error": (
                    hard_volume_error
                ),
                "predicted_volume_cm3": (
                    predicted_volume
                ),
                "observed_volume_cm3": (
                    observed_volume
                ),
                "max_c": float(
                    np.max(
                        calibrated_field
                    )
                ),
                "mass": float(
                    np.sum(
                        calibrated_field,
                        dtype=np.float64,
                    )
                ),
            }

            rows.append(
                row
            )

            print(
                f"D={best.diffusion:.4f}, "
                f"rho={best.proliferation:.4f}"
            )

            print(
                "soft Dice="
                f"{best.dice:.4f}, "
                "loss="
                f"{best.loss:.4f}"
            )

            print(
                "hard t1 Dice="
                f"{hard_dice:.4f}"
            )

            print(
                "volume error="
                f"{hard_volume_error:.2%}"
            )

            print(
                "max(c)="
                f"{np.max(calibrated_field):.6f}"
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

    summary = (
        result.groupby(
            "alpha_per_gy",
            as_index=False,
        )
        .agg(
            mean_calibration_loss=(
                "calibration_loss",
                "mean",
            ),
            mean_soft_dice=(
                "soft_dice",
                "mean",
            ),
            mean_hard_t1_dice=(
                "hard_t1_dice",
                "mean",
            ),
            mean_volume_error=(
                "hard_volume_error",
                "mean",
            ),
            mean_max_c=(
                "max_c",
                "mean",
            ),
        )
    )

    print()
    print("=" * 78)
    print(
        "V2 T0->T1 SUMMARY"
    )
    print("=" * 78)

    print(
        summary.to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.4f}"
            ),
        )
    )

    print()
    print(
        "PER-PATIENT BEST"
    )

    print(
        result[
            [
                "patient_id",
                "alpha_per_gy",
                "diffusion",
                "proliferation",
                "soft_dice",
                "calibration_loss",
                "hard_t1_dice",
                "hard_volume_error",
                "max_c",
            ]
        ].to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.4f}"
            ),
        )
    )

    print()
    print(
        f"Saved: {args.output}"
    )


if __name__ == "__main__":
    main()