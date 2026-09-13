from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    gaussian_initial_condition,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
)

RESULTS_DIR = Path("results")

TRAJECTORY_CSV = (
    RESULTS_DIR
    / "synthetic_post_rt_trajectory.csv"
)

TRAJECTORY_PLOT = (
    RESULTS_DIR
    / "synthetic_post_rt_trajectory.png"
)

SNAPSHOT_PLOT = (
    RESULTS_DIR
    / "synthetic_post_rt_snapshots.png"
)


def total_mass(
    field: np.ndarray,
) -> float:
    return float(
        np.sum(field)
    )


def simulate_at_day(
    initial: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    day: float,
    dt: float,
    treatment: (
        FractionatedRadiotherapy
        | RadiotherapyProtocol
        | None
    ),
) -> np.ndarray:
    return simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=day,
        dt=dt,
        treatment=treatment,
    )


def main() -> None:
    RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    shape = (
        48,
        48,
        48,
    )

    spacing = (
        1.0,
        1.0,
        1.0,
    )

    dt = 0.5

    end_day = 90.0

    observation_days = (
        0.0,
        10.0,
        15.0,
        20.0,
        26.0,
        30.0,
        40.0,
        50.0,
        60.0,
        75.0,
        90.0,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.03,
    )

    initial = gaussian_initial_condition(
        shape,
        sigma=3.0,
    )

    fraction_days = (
        15.0,
        16.0,
        17.0,
        18.0,
        19.0,
        22.0,
        23.0,
        24.0,
        25.0,
        26.0,
    )

    fractions = FractionatedRadiotherapy(
        fraction_days=fraction_days,
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.05,
        beta_per_gy2=0.005,
    )

    last_fraction_day = (
        fraction_days[-1]
    )

    short_post_effect = PostRadiotherapyEffect(
        start_day=last_fraction_day,
        initial_kill_rate=0.03,
        decay_time_days=14.0,
    )

    long_post_effect = PostRadiotherapyEffect(
        start_day=last_fraction_day,
        initial_kill_rate=0.03,
        decay_time_days=60.0,
    )

    short_protocol = RadiotherapyProtocol(
        fractions=fractions,
        post_effect=short_post_effect,
    )

    long_protocol = RadiotherapyProtocol(
        fractions=fractions,
        post_effect=long_post_effect,
    )

    scenarios = {
        "untreated": None,
        "fractionated_rt": fractions,
        "rt_short_memory": short_protocol,
        "rt_long_memory": long_protocol,
    }

    rows: list[
        dict[str, float | str]
    ] = []

    endpoint_fields: dict[
        str,
        np.ndarray,
    ] = {}

    print()
    print("=" * 60)
    print("SYNTHETIC POST-RT TRAJECTORY")
    print("=" * 60)

    for name, treatment in scenarios.items():
        print()
        print(
            f"Scenario: {name}"
        )

        for day in observation_days:
            field = simulate_at_day(
                initial,
                params,
                spacing=spacing,
                day=day,
                dt=dt,
                treatment=treatment,
            )

            mass = total_mass(
                field
            )

            rows.append(
                {
                    "scenario": name,
                    "day": day,
                    "mass": mass,
                }
            )

            print(
                f"  day {day:5.1f}: "
                f"mass={mass:.4f}"
            )

            if day == end_day:
                endpoint_fields[name] = field

    dataframe = pd.DataFrame(
        rows
    )

    initial_mass = total_mass(
        initial
    )

    dataframe[
        "relative_mass"
    ] = (
        dataframe["mass"]
        / initial_mass
    )

    dataframe.to_csv(
        TRAJECTORY_CSV,
        index=False,
    )

    endpoint_mass = {
        name: total_mass(field)
        for name, field
        in endpoint_fields.items()
    }

    print()
    print("=" * 60)
    print("DAY 90 SUMMARY")
    print("=" * 60)

    for name, mass in endpoint_mass.items():
        print(
            f"{name:20s} "
            f"{mass:.4f}"
        )

    untreated_mass = (
        endpoint_mass[
            "untreated"
        ]
    )

    fractionated_mass = (
        endpoint_mass[
            "fractionated_rt"
        ]
    )

    short_mass = (
        endpoint_mass[
            "rt_short_memory"
        ]
    )

    long_mass = (
        endpoint_mass[
            "rt_long_memory"
        ]
    )

    if not (
        fractionated_mass
        < untreated_mass
    ):
        raise RuntimeError(
            "Fractionated RT should suppress "
            "tumor mass relative to untreated"
        )

    if not (
        short_mass
        < fractionated_mass
    ):
        raise RuntimeError(
            "Short post-RT effect should suppress "
            "mass relative to fractionated RT alone"
        )

    if not (
        long_mass
        < short_mass
    ):
        raise RuntimeError(
            "Long post-RT effect should suppress "
            "mass more than short memory"
        )

    figure, axis = plt.subplots(
        figsize=(9, 5),
        layout="constrained",
    )

    for name in scenarios:
        subset = dataframe[
            dataframe["scenario"]
            == name
        ]

        axis.plot(
            subset["day"],
            subset["relative_mass"],
            marker="o",
            label=name,
        )

    axis.axvline(
        fraction_days[0],
        linestyle="--",
        alpha=0.5,
        label="first RT fraction",
    )

    axis.axvline(
        last_fraction_day,
        linestyle="--",
        alpha=0.5,
        label="last RT fraction",
    )

    axis.set_xlabel(
        "Day"
    )

    axis.set_ylabel(
        "Tumor mass / initial mass"
    )

    axis.set_title(
        "Synthetic tumor trajectory"
    )

    axis.legend()

    figure.savefig(
        TRAJECTORY_PLOT,
        dpi=150,
        bbox_inches="tight",
    )

    center_slice = (
        shape[2] // 2
    )

    snapshot_figure, axes = plt.subplots(
        1,
        4,
        figsize=(16, 4),
        layout="constrained",
    )

    image = None

    titles = {
        "untreated": "Untreated",
        "fractionated_rt": "Fractionated RT",
        "rt_short_memory": "RT + short memory",
        "rt_long_memory": "RT + long memory",
    }

    for axis, name in zip(
        axes,
        scenarios,
        strict=True,
    ):
        image = axis.imshow(
            endpoint_fields[name][
                :,
                :,
                center_slice,
            ],
            origin="lower",
            vmin=0.0,
            vmax=1.0,
        )

        axis.set_title(
            titles[name]
        )

        axis.set_axis_off()

    if image is None:
        raise RuntimeError(
            "No endpoint images generated"
        )

    snapshot_figure.colorbar(
        image,
        ax=axes.tolist(),
        location="right",
        shrink=0.8,
        pad=0.02,
        label="Tumor concentration",
    )

    snapshot_figure.suptitle(
        "Synthetic tumor at day 90"
    )

    snapshot_figure.savefig(
        SNAPSHOT_PLOT,
        dpi=150,
        bbox_inches="tight",
    )

    print()
    print(
        f"Saved: {TRAJECTORY_CSV}"
    )

    print(
        f"Saved: {TRAJECTORY_PLOT}"
    )

    print(
        f"Saved: {SNAPSHOT_PLOT}"
    )

    plt.show()


if __name__ == "__main__":
    main()