from __future__ import annotations

import argparse
import math
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
from gbm_twin.evaluation.metrics import (
    dice_score,
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

ALPHA_PER_GY = 0.01
ALPHA_BETA_RATIO_GY = 10.0

COARSE_DIFFUSION_VALUES = [
    0.0,
    0.005,
    0.015,
    0.030,
]

COARSE_PROLIFERATION_VALUES = [
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

TRANSITION_WIDTH_MM = 4.0

THRESHOLD = 0.5
SOFT_TEMPERATURE = 0.05
VOLUME_WEIGHT = 0.5
DT = 1.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Refine patient-specific D/rho for V2 "
            "using fixed PIRT alpha and t0->t1 only."
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
            "v2_latent_pirt_refined_t0_t1.csv"
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=2,
    )

    return parser.parse_args()


def build_refined_axis(
    values: list[float],
    best: float,
) -> list[float]:
    axis = sorted(
        set(values)
    )

    if not axis:
        raise ValueError(
            "values must not be empty"
        )

    if len(axis) == 1:
        return axis

    best_index = min(
        range(len(axis)),
        key=lambda index: abs(
            axis[index]
            - best
        ),
    )

    if not math.isclose(
        axis[best_index],
        best,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            f"Best value {best} is not "
            "present on the coarse axis"
        )

    candidates: list[float] = []

    if best_index == 0:
        right_step = (
            axis[1]
            - axis[0]
        ) / 2.0

        candidates.extend(
            [
                best,
                best + right_step,
            ]
        )

    elif (
        best_index
        == len(axis) - 1
    ):
        left_step = (
            axis[-1]
            - axis[-2]
        ) / 2.0

        candidates.extend(
            [
                best - left_step,
                best,
                best + left_step,
            ]
        )

    else:
        left = (
            axis[best_index - 1]
            + best
        ) / 2.0

        right = (
            best
            + axis[best_index + 1]
        ) / 2.0

        candidates.extend(
            [
                left,
                best,
                right,
            ]
        )

    return sorted(
        {
            round(
                max(0.0, value),
                12,
            )
            for value in candidates
        }
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
        float(
            np.count_nonzero(
                mask
            )
        )
        * voxel_volume_mm3
        / 1000.0
    )


def hard_metrics(
    field: np.ndarray,
    observed: np.ndarray,
    *,
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> tuple[
    float,
    float,
    float,
]:
    predicted = (
        field
        >= THRESHOLD
    )

    dice = dice_score(
        predicted,
        observed,
    )

    predicted_volume = volume_cm3(
        predicted,
        spacing=spacing,
    )

    observed_volume = volume_cm3(
        observed,
        spacing=spacing,
    )

    if observed_volume > 0:
        volume_error = (
            abs(
                predicted_volume
                - observed_volume
            )
            / observed_volume
        )
    else:
        volume_error = float(
            "nan"
        )

    return (
        dice,
        volume_error,
        predicted_volume,
    )


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

    radiobiology = (
        RadiobiologyParameters(
            alpha_per_gy=(
                ALPHA_PER_GY
            ),
            alpha_beta_ratio_gy=(
                ALPHA_BETA_RATIO_GY
            ),
        )
    )

    rows: list[
        dict[str, float | int]
    ] = []

    print()
    print("=" * 78)
    print(
        "V2 PIRT D/RHO REFINEMENT"
    )
    print("=" * 78)

    print(
        f"Patients: {list(PATIENT_IDS)}"
    )

    print(
        "Fixed effective alpha: "
        f"{ALPHA_PER_GY:.4f} /Gy"
    )

    print(
        "Transition width: "
        f"{TRANSITION_WIDTH_MM:.2f} mm"
    )

    print(
        "IMPORTANT: only t0 and t1 "
        "are loaded."
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
                "RT schedule cannot be reconstructed"
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

        treatment = (
            build_pirt_radiotherapy(
                schedule,
                radiobiology,
            )
        )

        print()
        print("=" * 78)
        print(
            f"PATIENT {patient_id}"
        )
        print("=" * 78)

        coarse_results = grid_search(
            initial,
            observed_t1,
            domain,
            spacing=t0_gtv.spacing,
            duration_days=dt01,
            dt=DT,
            diffusion_values=(
                COARSE_DIFFUSION_VALUES
            ),
            proliferation_values=(
                COARSE_PROLIFERATION_VALUES
            ),
            threshold=THRESHOLD,
            volume_weight=(
                VOLUME_WEIGHT
            ),
            treatment=treatment,
            start_time_day=0.0,
            cache_dir=args.cache_dir,
            workers=args.workers,
            objective="soft",
            soft_temperature=(
                SOFT_TEMPERATURE
            ),
        )

        if not coarse_results:
            raise RuntimeError(
                "Coarse calibration returned "
                "no candidates"
            )

        coarse_best = (
            coarse_results[0]
        )

        refined_diffusion_values = (
            build_refined_axis(
                COARSE_DIFFUSION_VALUES,
                coarse_best.diffusion,
            )
        )

        refined_proliferation_values = (
            build_refined_axis(
                COARSE_PROLIFERATION_VALUES,
                coarse_best.proliferation,
            )
        )

        print()
        print(
            "Coarse best: "
            f"D={coarse_best.diffusion:.4f}, "
            f"rho={coarse_best.proliferation:.4f}, "
            f"loss={coarse_best.loss:.4f}"
        )

        print(
            "Refined D: "
            f"{refined_diffusion_values}"
        )

        print(
            "Refined rho: "
            f"{refined_proliferation_values}"
        )

        refined_results = grid_search(
            initial,
            observed_t1,
            domain,
            spacing=t0_gtv.spacing,
            duration_days=dt01,
            dt=DT,
            diffusion_values=(
                refined_diffusion_values
            ),
            proliferation_values=(
                refined_proliferation_values
            ),
            threshold=THRESHOLD,
            volume_weight=(
                VOLUME_WEIGHT
            ),
            treatment=treatment,
            start_time_day=0.0,
            cache_dir=args.cache_dir,
            workers=args.workers,
            objective="soft",
            soft_temperature=(
                SOFT_TEMPERATURE
            ),
        )

        if not refined_results:
            raise RuntimeError(
                "Refined calibration returned "
                "no candidates"
            )

        best = refined_results[0]

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
                treatment=treatment,
                start_time_day=0.0,
            )
        )

        (
            hard_dice,
            hard_volume_error,
            predicted_volume,
        ) = hard_metrics(
            calibrated_field,
            observed_t1,
            spacing=t0_gtv.spacing,
        )

        observed_volume = (
            volume_cm3(
                observed_t1,
                spacing=t0_gtv.spacing,
            )
        )

        loss_improvement = (
            coarse_best.loss
            - best.loss
        )

        rows.append(
            {
                "patient_id": (
                    patient_id
                ),
                "alpha_per_gy": (
                    ALPHA_PER_GY
                ),
                "dt01_days": (
                    dt01
                ),
                "transition_width_mm": (
                    TRANSITION_WIDTH_MM
                ),
                "coarse_diffusion": (
                    coarse_best.diffusion
                ),
                "coarse_proliferation": (
                    coarse_best.proliferation
                ),
                "coarse_loss": (
                    coarse_best.loss
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
                "loss_improvement": (
                    loss_improvement
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
        )

        print(
            "Refined best: "
            f"D={best.diffusion:.4f}, "
            f"rho={best.proliferation:.4f}"
        )

        print(
            "Soft Dice="
            f"{best.dice:.4f}, "
            "loss="
            f"{best.loss:.4f}"
        )

        print(
            "Loss improvement="
            f"{loss_improvement:+.4f}"
        )

        print(
            "Hard t1 Dice="
            f"{hard_dice:.4f}"
        )

        print(
            "Hard volume error="
            f"{hard_volume_error:.2%}"
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
    print("=" * 78)
    print(
        "V2 REFINED T0->T1 SUMMARY"
    )
    print("=" * 78)

    print(
        "Patients: "
        f"{len(result)}"
    )

    print(
        "Mean coarse loss: "
        f"{result['coarse_loss'].mean():.4f}"
    )

    print(
        "Mean refined loss: "
        f"{result['calibration_loss'].mean():.4f}"
    )

    print(
        "Mean loss improvement: "
        f"{result['loss_improvement'].mean():+.4f}"
    )

    print(
        "Mean soft Dice: "
        f"{result['soft_dice'].mean():.4f}"
    )

    print(
        "Mean hard t1 Dice: "
        f"{result['hard_t1_dice'].mean():.4f}"
    )

    print(
        "Mean hard volume error: "
        f"{result['hard_volume_error'].mean():.2%}"
    )

    print()
    print(
        "PER-PATIENT REFINED PARAMETERS"
    )

    print(
        result[
            [
                "patient_id",
                "coarse_diffusion",
                "coarse_proliferation",
                "diffusion",
                "proliferation",
                "coarse_loss",
                "calibration_loss",
                "soft_dice",
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