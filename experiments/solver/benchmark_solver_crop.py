import time

import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)


def build_case() -> tuple[
    np.ndarray,
    np.ndarray,
]:
    shape = (
        130,
        130,
        105,
    )

    coordinates = np.indices(
        shape,
        dtype=np.float32,
    )

    center = np.asarray(
        [
            (size - 1) / 2.0
            for size in shape
        ],
        dtype=np.float32,
    )

    tumor_distance = np.zeros(
        shape,
        dtype=np.float32,
    )

    brain_distance = np.zeros(
        shape,
        dtype=np.float32,
    )

    for axis in range(3):
        delta = (
            coordinates[axis]
            - center[axis]
        )

        tumor_distance += (
            delta
            / (
                shape[axis]
                * 0.08
            )
        ) ** 2

        brain_distance += (
            delta
            / (
                shape[axis]
                * 0.45
            )
        ) ** 2

    initial = np.exp(
        -0.5
        * tumor_distance
    ).astype(
        np.float32
    )

    domain = (
        brain_distance
        <= 1.0
    )

    initial[
        ~domain
    ] = 0.0

    return (
        initial,
        domain,
    )


def run(
    initial: np.ndarray,
    domain: np.ndarray,
    *,
    crop_to_domain: bool,
) -> tuple[np.ndarray, float]:
    params = ReactionDiffusionParameters(
        diffusion=0.01,
        proliferation=0.04,
    )

    started = time.perf_counter()

    result = simulate_reaction_diffusion(
        initial,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=168.0,
        dt=2.0,
        domain_mask=domain,
        crop_to_domain=crop_to_domain,
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    return (
        result,
        elapsed,
    )


def main() -> None:
    initial, domain = (
        build_case()
    )

    print()
    print("=" * 60)
    print("FULL DOMAIN")
    print("=" * 60)

    full, full_time = run(
        initial,
        domain,
        crop_to_domain=False,
    )

    print(
        f"Elapsed: {full_time:.3f} s"
    )

    print()
    print("=" * 60)
    print("CROPPED DOMAIN")
    print("=" * 60)

    cropped, cropped_time = run(
        initial,
        domain,
        crop_to_domain=True,
    )

    print(
        f"Elapsed: {cropped_time:.3f} s"
    )

    difference = np.abs(
        full
        - cropped
    )

    print()
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)

    print(
        f"Speedup: "
        f"{full_time / cropped_time:.3f}x"
    )

    print(
        f"Max absolute error: "
        f"{float(np.max(difference)):.8e}"
    )

    voxel_disagreement = int(
        np.count_nonzero(
            (full >= 0.5)
            != (cropped >= 0.5)
        )
    )

    print(
        "Voxel disagreement @0.5: "
        f"{voxel_disagreement}"
    )


if __name__ == "__main__":
    main()