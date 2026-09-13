import matplotlib.pyplot as plt
import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    gaussian_initial_condition,
)
from gbm_twin.models.solver import simulate_reaction_diffusion


def main() -> None:
    shape = (64, 64, 64)
    spacing = (1.0, 1.0, 1.0)

    initial = gaussian_initial_condition(
        shape,
        sigma=3.0,
    )

    params = ReactionDiffusionParameters(
        diffusion=0.1,
        proliferation=0.03,
    )

    result = simulate_reaction_diffusion(
        initial,
        params,
        spacing=spacing,
        duration_days=30.0,
        dt=0.5,
    )

    slice_index = shape[2] // 2

    fig, axes = plt.subplots(1, 2, figsize=(10, 5))

    axes[0].imshow(
        np.rot90(initial[:, :, slice_index]),
        vmin=0,
        vmax=1,
    )
    axes[0].set_title("Day 0")
    axes[0].axis("off")

    axes[1].imshow(
        np.rot90(result[:, :, slice_index]),
        vmin=0,
        vmax=1,
    )
    axes[1].set_title("Day 30")
    axes[1].axis("off")

    plt.tight_layout()
    plt.show()

    print("Initial mass:", initial.sum())
    print("Final mass:", result.sum())
    print("Initial max:", initial.max())
    print("Final max:", result.max())


if __name__ == "__main__":
    main()