from pathlib import Path

import numpy as np
import pandas as pd

from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.models.pirt_solver import (
    simulate_reaction_diffusion_pirt,
)
from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.rt_schedule import (
    build_fractionated_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)

OUTPUT = Path(
    "results/synthetic_rt_model_comparison.csv"
)

SHAPE = (
    65,
    65,
    65,
)

SPACING = (
    2.0,
    2.0,
    2.0,
)

BRAIN_RADIUS_MM = 50.0
GTV_RADIUS_MM = 16.0

TRANSITION_WIDTH_MM = 4.0

TOTAL_DOSE_GY = 60.0
FRACTIONS = 30
RT_START_DAY = 1.0

ALPHA_PER_GY = 0.10
ALPHA_BETA_RATIO_GY = 10.0

DT = 1.0

SCENARIOS = {
    "static": ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    ),
    "growing": ReactionDiffusionParameters(
        diffusion=0.005,
        proliferation=0.055,
    ),
}


def synthetic_masks() -> tuple[
    np.ndarray,
    np.ndarray,
]:
    axes = [
        (
            np.arange(
                size,
                dtype=np.float64,
            )
            - (size - 1) / 2.0
        )
        * spacing
        for size, spacing in zip(
            SHAPE,
            SPACING,
            strict=True,
        )
    ]

    x, y, z = np.meshgrid(
        *axes,
        indexing="ij",
    )

    radius = np.sqrt(
        x**2
        + y**2
        + z**2
    )

    brain = (
        radius
        <= BRAIN_RADIUS_MM
    )

    gtv = (
        radius
        <= GTV_RADIUS_MM
    )

    return (
        gtv,
        brain,
    )


def volume_cm3(
    mask: np.ndarray,
) -> float:
    voxel_volume_mm3 = float(
        np.prod(
            np.asarray(
                SPACING,
                dtype=np.float64,
            )
        )
    )

    return (
        float(
            np.count_nonzero(mask)
        )
        * voxel_volume_mm3
        / 1000.0
    )


def field_metrics(
    field: np.ndarray,
) -> dict[str, float]:
    return {
        "max_c": float(
            np.max(field)
        ),
        "mass": float(
            np.sum(
                field,
                dtype=np.float64,
            )
        ),
        "volume_ge_050_cm3": (
            volume_cm3(
                field >= 0.50
            )
        ),
        "volume_ge_016_cm3": (
            volume_cm3(
                field >= 0.16
            )
        ),
    }


def result_row(
    *,
    scenario: str,
    model: str,
    field: np.ndarray,
) -> dict[str, float | str]:
    metrics = field_metrics(
        field
    )

    return {
        "scenario": scenario,
        "model": model,
        **metrics,
    }


def main() -> None:
    gtv, brain = synthetic_masks()

    initial = latent_state_from_gtv(
        gtv,
        brain,
        spacing=SPACING,
        parameters=LatentStateParameters(
            transition_width_mm=(
                TRANSITION_WIDTH_MM
            )
        ),
    )

    schedule = (
        reconstruct_weekday_like_schedule(
            start_day=RT_START_DAY,
            total_dose_gy=(
                TOTAL_DOSE_GY
            ),
            fractions_number=(
                FRACTIONS
            ),
        )
    )

    if (
        len(schedule.fraction_days)
        != FRACTIONS
    ):
        raise RuntimeError(
            "Unexpected reconstructed "
            "fraction count"
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

    multiplicative_rt = (
        build_fractionated_radiotherapy(
            schedule,
            radiobiology,
        )
    )

    dose_per_fraction = (
        TOTAL_DOSE_GY
        / FRACTIONS
    )

    beta_per_gy2 = (
        ALPHA_PER_GY
        / ALPHA_BETA_RATIO_GY
    )

    survival_fraction = float(
        np.exp(
            -(
                ALPHA_PER_GY
                * dose_per_fraction
                + beta_per_gy2
                * dose_per_fraction**2
            )
        )
    )

    cumulative_survival = (
        survival_fraction
        ** FRACTIONS
    )

    last_fraction_day = float(
        schedule.fraction_days[-1]
    )

    duration_days = (
        last_fraction_day
        + 1.0
    )

    print()
    print("=" * 72)
    print(
        "SYNTHETIC RT MODEL COMPARISON"
    )
    print("=" * 72)

    print(
        f"Initial max(c): "
        f"{np.max(initial):.6f}"
    )

    print(
        f"Initial mass: "
        f"{np.sum(initial):.3f}"
    )

    print(
        "RT: "
        f"{TOTAL_DOSE_GY:.1f} Gy / "
        f"{FRACTIONS} fractions"
    )

    print(
        "Dose per fraction: "
        f"{dose_per_fraction:.3f} Gy"
    )

    print(
        "LQ survival per fraction: "
        f"{survival_fraction:.6f}"
    )

    print(
        "Plain multiplicative "
        "cumulative survival: "
        f"{cumulative_survival:.8f}"
    )

    print(
        "Last fraction day: "
        f"{last_fraction_day:.1f}"
    )

    rows: list[
        dict[str, float | str]
    ] = []

    for (
        scenario_name,
        parameters,
    ) in SCENARIOS.items():
        print()
        print("-" * 72)

        print(
            f"SCENARIO: "
            f"{scenario_name}"
        )

        print(
            f"D={parameters.diffusion:.4f}, "
            f"rho="
            f"{parameters.proliferation:.4f}"
        )

        untreated = (
            simulate_reaction_diffusion(
                initial,
                parameters,
                spacing=SPACING,
                duration_days=(
                    duration_days
                ),
                dt=DT,
                domain_mask=brain,
                treatment=None,
                start_time_day=0.0,
            )
        )

        multiplicative = (
            simulate_reaction_diffusion(
                initial,
                parameters,
                spacing=SPACING,
                duration_days=(
                    duration_days
                ),
                dt=DT,
                domain_mask=brain,
                treatment=(
                    multiplicative_rt
                ),
                start_time_day=0.0,
            )
        )

        pirt = (
            simulate_reaction_diffusion_pirt(
                initial,
                parameters,
                spacing=SPACING,
                duration_days=(
                    duration_days
                ),
                dt=DT,
                domain_mask=brain,
                fraction_days=tuple(
                    float(day)
                    for day
                    in schedule.fraction_days
                ),
                survival_fraction=(
                    survival_fraction
                ),
                start_time_day=0.0,
            )
        )

        fields = {
            "untreated": untreated,
            "multiplicative_rt": (
                multiplicative
            ),
            "pirt_rt": pirt,
        }

        for model, field in fields.items():
            metrics = field_metrics(
                field
            )

            rows.append(
                result_row(
                    scenario=(
                        scenario_name
                    ),
                    model=model,
                    field=field,
                )
            )

            print()
            print(model)

            print(
                "  max(c): "
                f"{metrics['max_c']:.6f}"
            )

            print(
                "  mass: "
                f"{metrics['mass']:.3f}"
            )

            print(
                "  volume c>=0.50: "
                f"{metrics['volume_ge_050_cm3']:.3f} "
                "cm3"
            )

            print(
                "  volume c>=0.16: "
                f"{metrics['volume_ge_016_cm3']:.3f} "
                "cm3"
            )

    result = pd.DataFrame(
        rows
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_csv(
        OUTPUT,
        index=False,
    )

    print()
    print("=" * 72)
    print(
        "SUMMARY"
    )
    print("=" * 72)

    print(
        result.to_string(
            index=False,
            float_format=lambda value: (
                f"{value:.6f}"
            ),
        )
    )

    print()
    print(
        f"Saved: {OUTPUT}"
    )


if __name__ == "__main__":
    main()