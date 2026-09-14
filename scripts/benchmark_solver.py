import argparse
import time

import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark the 3D reaction-diffusion solver."
    )

    parser.add_argument(
        "--shape",
        type=int,
        nargs=3,
        default=[130, 130, 105],
        metavar=("NX", "NY", "NZ"),
    )

    parser.add_argument(
        "--duration",
        type=float,
        default=168.0,
    )

    parser.add_argument(
        "--dt",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--diffusion",
        type=float,
        default=0.01,
    )

    parser.add_argument(
        "--rho",
        type=float,
        default=0.04,
    )

    return parser.parse_args()


def build_synthetic_case(
    shape: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    coordinates = np.indices(
        shape,
        dtype=np.float64,
    )

    center = np.asarray(
        [
            (size - 1) / 2.0
            for size in shape
        ],
        dtype=np.float64,
    )

    normalized_distance_squared = np.zeros(
        shape,
        dtype=np.float64,
    )

    domain_distance_squared = np.zeros(
        shape,
        dtype=np.float64,
    )

    for axis in range(3):
        delta = (
            coordinates[axis]
            - center[axis]
        )

        normalized_distance_squared += (
            delta
            / (shape[axis] * 0.08)
        ) ** 2

        domain_distance_squared += (
            delta
            / (shape[axis] * 0.45)
        ) ** 2

    initial_field = np.exp(
        -0.5
        * normalized_distance_squared
    )

    domain_mask = (
        domain_distance_squared
        <= 1.0
    )

    initial_field[
        ~domain_mask
    ] = 0.0

    return (
        initial_field,
        domain_mask,
    )


def main() -> None:
    args = parse_args()

    shape = tuple(
        args.shape
    )

    initial_field, domain_mask = (
        build_synthetic_case(
            shape
        )
    )

    params = ReactionDiffusionParameters(
        diffusion=args.diffusion,
        proliferation=args.rho,
    )

    steps = int(
        np.ceil(
            args.duration
            / args.dt
        )
    )

    print()
    print("=" * 60)
    print("SOLVER BENCHMARK")
    print("=" * 60)

    print(
        f"Shape: {shape}"
    )

    print(
        f"Voxels: "
        f"{np.prod(shape):,}"
    )

    print(
        f"Duration: "
        f"{args.duration:.1f} days"
    )

    print(
        f"dt: {args.dt:.2f} days"
    )

    print(
        f"Approx. steps: {steps}"
    )

    print(
        f"D: {args.diffusion:.4f}"
    )

    print(
        f"rho: {args.rho:.4f}"
    )

    started = time.perf_counter()

    result = simulate_reaction_diffusion(
        initial_field,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=args.duration,
        dt=args.dt,
        domain_mask=domain_mask,
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    print()
    print("=" * 60)
    print("RESULT")
    print("=" * 60)

    print(
        f"Elapsed: {elapsed:.3f} s"
    )

    print(
        f"Time / step: "
        f"{elapsed / steps:.4f} s"
    )

    print(
        f"Result mass: "
        f"{float(np.sum(result)):.4f}"
    )

    print(
        f"Result max: "
        f"{float(np.max(result)):.6f}"
    )


if __name__ == "__main__":
    main()