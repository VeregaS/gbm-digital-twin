from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    gaussian_initial_condition,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    TreatmentWindow,
)


def total_mass(
    field: np.ndarray,
) -> float:
    return float(
        np.sum(field)
    )


def main() -> None:
    shape = (
        64,
        64,
        64,
    )

    spacing = (
        1.0,
        1.0,
        1.0,
    )

    duration_days = 45.0
    dt = 0.5

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.03,
    )

    initial = gaussian_initial_condition(
        shape,
        sigma=3.0,
    )

    # Synthetic weekday-like fraction schedule:
    # 5 fractions, weekend gap, then 5 fractions.
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

    dose_per_fraction_gy = 2.0

    # Synthetic radiosensitivity parameters.
    alpha_per_gy = 0.05
    beta_per_gy2 = 0.005

    fractionated_rt = (
        FractionatedRadiotherapy(
            fraction_days=fraction_days,
            dose_per_fraction_gy=(
                dose_per_fraction_gy
            ),
            alpha_per_gy=alpha_per_gy,
            beta_per_gy2=beta_per_gy2,
        )
    )

    log_kill_per_fraction = (
        alpha_per_gy
        * dose_per_fraction_gy
        + beta_per_gy2
        * dose_per_fraction_gy**2
    )

    total_log_kill = (
        len(fraction_days)
        * log_kill_per_fraction
    )

    continuous_start_day = (
        fraction_days[0]
    )

    continuous_end_day = (
        fraction_days[-1]
        + 1.0
    )

    continuous_duration = (
        continuous_end_day
        - continuous_start_day
    )

    equivalent_kill_rate = (
        total_log_kill
        / continuous_duration
    )

    continuous_rt = TreatmentWindow(
        start_day=continuous_start_day,
        end_day=continuous_end_day,
        kill_rate=equivalent_kill_rate,
    )

    untreated = simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
    )

    continuous = simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
        treatment=continuous_rt,
    )

    fractionated = simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
        treatment=fractionated_rt,
    )

    initial_mass = total_mass(
        initial
    )

    untreated_mass = total_mass(
        untreated
    )

    continuous_mass = total_mass(
        continuous
    )

    fractionated_mass = total_mass(
        fractionated
    )

    print(
        f"Initial mass: "
        f"{initial_mass:.4f}"
    )

    print(
        f"Untreated mass at day "
        f"{duration_days:.0f}: "
        f"{untreated_mass:.4f}"
    )

    print(
        f"Continuous RT mass at day "
        f"{duration_days:.0f}: "
        f"{continuous_mass:.4f}"
    )

    print(
        f"Fractionated RT mass at day "
        f"{duration_days:.0f}: "
        f"{fractionated_mass:.4f}"
    )

    print()

    print(
        "Fractionated total dose: "
        f"{fractionated_rt.total_dose_gy:.2f} Gy"
    )

    print(
        "Fraction survival per fraction: "
        f"{fractionated_rt.survival_fraction_per_fraction:.4f}"
    )

    print(
        "Nominal cumulative log-kill: "
        f"{total_log_kill:.4f}"
    )

    print(
        "Equivalent continuous kill rate: "
        f"{equivalent_kill_rate:.4f} /day"
    )

    print()

    print(
        "Continuous / untreated mass: "
        f"{continuous_mass / untreated_mass:.4f}"
    )

    print(
        "Fractionated / untreated mass: "
        f"{fractionated_mass / untreated_mass:.4f}"
    )

    print()

    print(
        "Untreated max concentration: "
        f"{float(np.max(untreated)):.4f}"
    )

    print(
        "Continuous max concentration: "
        f"{float(np.max(continuous)):.4f}"
    )

    print(
        "Fractionated max concentration: "
        f"{float(np.max(fractionated)):.4f}"
    )

    if continuous_mass >= untreated_mass:
        raise RuntimeError(
            "Continuous treatment sanity "
            "check failed"
        )

    if fractionated_mass >= untreated_mass:
        raise RuntimeError(
            "Fractionated treatment sanity "
            "check failed"
        )

    center_slice = (
        shape[2] // 2
    )

    figure, axes = plt.subplots(
        1,
        4,
        figsize=(16, 4),
        layout="constrained",
    )

    image = axes[0].imshow(
        initial[
            :,
            :,
            center_slice,
        ],
        origin="lower",
        vmin=0.0,
        vmax=1.0,
    )

    axes[0].set_title(
        "Day 0"
    )

    axes[1].imshow(
        untreated[
            :,
            :,
            center_slice,
        ],
        origin="lower",
        vmin=0.0,
        vmax=1.0,
    )

    axes[1].set_title(
        "Day 45 — untreated"
    )

    axes[2].imshow(
        continuous[
            :,
            :,
            center_slice,
        ],
        origin="lower",
        vmin=0.0,
        vmax=1.0,
    )

    axes[2].set_title(
        "Day 45 — continuous RT"
    )

    axes[3].imshow(
        fractionated[
            :,
            :,
            center_slice,
        ],
        origin="lower",
        vmin=0.0,
        vmax=1.0,
    )

    axes[3].set_title(
        "Day 45 — fractionated RT"
    )

    for axis in axes:
        axis.set_axis_off()

    figure.colorbar(
        image,
        ax=axes.tolist(),
        location="right",
        shrink=0.8,
        pad=0.02,
        label="Tumor concentration",
    )

    output_dir = Path(
        "results"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "synthetic_fractionated_treatment.png"
    )

    figure.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    print()
    print(
        f"Saved: {output_path}"
    )

    plt.show()


if __name__ == "__main__":
    main()