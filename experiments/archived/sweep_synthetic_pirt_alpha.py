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
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.rt_schedule import (
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)

OUTPUT = Path(
    "results/synthetic_pirt_alpha_sweep.csv"
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

ALPHA_BETA_RATIO_GY = 10.0

ALPHAS = (
    0.01,
    0.025,
    0.05,
    0.075,
    0.10,
)

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
        "volume_ge_050_cm3": volume_cm3(
            field >= 0.50
        ),
        "volume_ge_016_cm3": volume_cm3(
            field >= 0.16
        ),
    }


def survival_fraction(
    alpha_per_gy: float,
) -> float:
    dose_per_fraction = (
        TOTAL_DOSE_GY
        / FRACTIONS
    )

    beta_per_gy2 = (
        alpha_per_gy
        / ALPHA_BETA_RATIO_GY
    )

    return float(
        np.exp(
            -(
                alpha_per_gy
                * dose_per_fraction
                + beta_per_gy2
                * dose_per_fraction**2
            )
        )
    )


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
            fractions_number=FRACTIONS,
        )
    )

    fraction_days = tuple(
        float(day)
        for day in schedule.fraction_days
    )

    if (
        len(fraction_days)
        != FRACTIONS
    ):
        raise RuntimeError(
            "Unexpected reconstructed "
            "fraction count"
        )

    duration_days = (
        fraction_days[-1]
        + 1.0
    )

    rows: list[
        dict[str, float | str]
    ] = []

    print()
    print("=" * 78)
    print(
        "SYNTHETIC PIRT ALPHA SENSITIVITY"
    )
    print("=" * 78)

    print(
        f"RT: {TOTAL_DOSE_GY:.1f} Gy / "
        f"{FRACTIONS} fractions"
    )

    print(
        "alpha/beta: "
        f"{ALPHA_BETA_RATIO_GY:.1f} Gy"
    )

    print(
        "alphas: "
        f"{list(ALPHAS)}"
    )

    for (
        scenario_name,
        parameters,
    ) in SCENARIOS.items():
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

        untreated_metrics = (
            field_metrics(
                untreated
            )
        )

        print()
        print("-" * 78)

        print(
            f"SCENARIO: "
            f"{scenario_name}"
        )

        print(
            "Untreated:"
        )

        print(
            "  max(c): "
            f"{untreated_metrics['max_c']:.6f}"
        )

        print(
            "  mass: "
            f"{untreated_metrics['mass']:.3f}"
        )

        print(
            "  volume c>=0.50: "
            f"{untreated_metrics['volume_ge_050_cm3']:.3f} "
            "cm3"
        )

        for alpha in ALPHAS:
            survival = (
                survival_fraction(
                    alpha
                )
            )

            cumulative_survival = (
                survival
                ** FRACTIONS
            )

            field = (
                simulate_reaction_diffusion_pirt(
                    initial,
                    parameters,
                    spacing=SPACING,
                    duration_days=(
                        duration_days
                    ),
                    dt=DT,
                    domain_mask=brain,
                    fraction_days=(
                        fraction_days
                    ),
                    survival_fraction=(
                        survival
                    ),
                    start_time_day=0.0,
                )
            )

            metrics = field_metrics(
                field
            )

            untreated_mass = (
                untreated_metrics[
                    "mass"
                ]
            )

            if untreated_mass > 0:
                mass_ratio = (
                    metrics["mass"]
                    / untreated_mass
                )
            else:
                mass_ratio = float(
                    "nan"
                )

            untreated_volume = (
                untreated_metrics[
                    "volume_ge_050_cm3"
                ]
            )

            if untreated_volume > 0:
                volume_ratio = (
                    metrics[
                        "volume_ge_050_cm3"
                    ]
                    / untreated_volume
                )
            else:
                volume_ratio = float(
                    "nan"
                )

            rows.append(
                {
                    "scenario": (
                        scenario_name
                    ),
                    "alpha_per_gy": (
                        alpha
                    ),
                    "survival_per_fraction": (
                        survival
                    ),
                    "plain_cumulative_survival": (
                        cumulative_survival
                    ),
                    "max_c": (
                        metrics["max_c"]
                    ),
                    "mass": (
                        metrics["mass"]
                    ),
                    "mass_ratio_to_untreated": (
                        mass_ratio
                    ),
                    "volume_ge_050_cm3": (
                        metrics[
                            "volume_ge_050_cm3"
                        ]
                    ),
                    "volume_050_ratio_to_untreated": (
                        volume_ratio
                    ),
                    "volume_ge_016_cm3": (
                        metrics[
                            "volume_ge_016_cm3"
                        ]
                    ),
                }
            )

            print()
            print(
                f"alpha={alpha:.3f}"
            )

            print(
                "  S/fraction: "
                f"{survival:.6f}"
            )

            print(
                "  plain S^N: "
                f"{cumulative_survival:.6f}"
            )

            print(
                "  max(c): "
                f"{metrics['max_c']:.6f}"
            )

            print(
                "  mass: "
                f"{metrics['mass']:.3f}"
            )

            print(
                "  mass / untreated: "
                f"{mass_ratio:.4f}"
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
    print("=" * 78)
    print("SUMMARY")
    print("=" * 78)

    columns = [
        "scenario",
        "alpha_per_gy",
        "survival_per_fraction",
        "max_c",
        "mass",
        "mass_ratio_to_untreated",
        "volume_ge_050_cm3",
        "volume_ge_016_cm3",
    ]

    print(
        result[
            columns
        ].to_string(
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