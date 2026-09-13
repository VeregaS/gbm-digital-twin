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

    treatment = TreatmentWindow(
        start_day=15.0,
        end_day=30.0,
        kill_rate=0.06,
    )

    initial = gaussian_initial_condition(
        shape,
        sigma=3.0,
    )

    untreated = simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
    )

    treated = simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=duration_days,
        dt=dt,
        treatment=treatment,
    )

    initial_mass = total_mass(
        initial
    )

    untreated_mass = total_mass(
        untreated
    )

    treated_mass = total_mass(
        treated
    )

    print(
        f"Initial mass: {initial_mass:.4f}"
    )

    print(
        f"Untreated mass at day "
        f"{duration_days:.0f}: "
        f"{untreated_mass:.4f}"
    )

    print(
        f"Treated mass at day "
        f"{duration_days:.0f}: "
        f"{treated_mass:.4f}"
    )

    print(
        "Treated / untreated mass: "
        f"{treated_mass / untreated_mass:.4f}"
    )

    print(
        "Untreated max concentration: "
        f"{float(np.max(untreated)):.4f}"
    )

    print(
        "Treated max concentration: "
        f"{float(np.max(treated)):.4f}"
    )

    if treated_mass >= untreated_mass:
        raise RuntimeError(
            "Treatment sanity check failed: "
            "treated mass is not lower than "
            "untreated mass"
        )

    center_slice = (
        shape[2] // 2
    )

    figure, axes = plt.subplots(
        1,
        3,
        figsize=(13, 4),
        layout="constrained",
    )

    image_initial = axes[0].imshow(
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
        treated[
            :,
            :,
            center_slice,
        ],
        origin="lower",
        vmin=0.0,
        vmax=1.0,
    )

    axes[2].set_title(
        "Day 45 — treatment"
    )

    for axis in axes:
        axis.set_axis_off()

    figure.colorbar(
        image_initial,
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
        / "synthetic_treatment.png"
    )

    figure.savefig(
        output_path,
        dpi=150,
        bbox_inches="tight",
    )

    print(
        f"Saved: {output_path}"
    )

    plt.show()


if __name__ == "__main__":
    main()