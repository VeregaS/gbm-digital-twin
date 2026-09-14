import argparse
import time

import numpy as np

from gbm_twin.evaluation.metrics import (
    dice_score,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare float64 and float32 "
            "reaction-diffusion solver performance."
        )
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

    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
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

    tumor_distance_squared = np.zeros(
        shape,
        dtype=np.float64,
    )

    brain_distance_squared = np.zeros(
        shape,
        dtype=np.float64,
    )

    for axis in range(3):
        delta = (
            coordinates[axis]
            - center[axis]
        )

        tumor_distance_squared += (
            delta
            / (shape[axis] * 0.08)
        ) ** 2

        brain_distance_squared += (
            delta
            / (shape[axis] * 0.45)
        ) ** 2

    initial = np.exp(
        -0.5
        * tumor_distance_squared
    )

    domain = (
        brain_distance_squared
        <= 1.0
    )

    initial[
        ~domain
    ] = 0.0

    return (
        initial,
        domain,
    )


def run_solver(
    initial: np.ndarray,
    domain: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    duration_days: float,
    dt: float,
) -> tuple[np.ndarray, float]:
    started = time.perf_counter()

    result = simulate_reaction_diffusion(
        initial,
        params,
        spacing=(2.0, 2.0, 2.0),
        duration_days=duration_days,
        dt=dt,
        domain_mask=domain,
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
    args = parse_args()

    shape = tuple(
        args.shape
    )

    initial, domain = (
        build_synthetic_case(
            shape
        )
    )

    params = ReactionDiffusionParameters(
        diffusion=args.diffusion,
        proliferation=args.rho,
    )

    initial64 = initial.astype(
        np.float64
    )

    initial32 = initial.astype(
        np.float32
    )

    print()
    print("=" * 60)
    print("FLOAT64")
    print("=" * 60)

    result64, elapsed64 = run_solver(
        initial64,
        domain,
        params,
        duration_days=args.duration,
        dt=args.dt,
    )

    print(
        f"Elapsed: {elapsed64:.3f} s"
    )

    print(
        f"Mass: "
        f"{float(np.sum(result64)):.6f}"
    )

    print(
        f"Max: "
        f"{float(np.max(result64)):.8f}"
    )

    print(
        f"Dtype: {result64.dtype}"
    )

    print()
    print("=" * 60)
    print("FLOAT32")
    print("=" * 60)

    result32, elapsed32 = run_solver(
        initial32,
        domain,
        params,
        duration_days=args.duration,
        dt=args.dt,
    )

    print(
        f"Elapsed: {elapsed32:.3f} s"
    )

    print(
        f"Mass: "
        f"{float(np.sum(result32)):.6f}"
    )

    print(
        f"Max: "
        f"{float(np.max(result32)):.8f}"
    )

    print(
        f"Dtype: {result32.dtype}"
    )

    difference = (
        result64
        - result32.astype(
            np.float64
        )
    )

    max_abs_error = float(
        np.max(
            np.abs(
                difference
            )
        )
    )

    mean_abs_error = float(
        np.mean(
            np.abs(
                difference
            )
        )
    )

    mass64 = float(
        np.sum(
            result64,
            dtype=np.float64,
        )
    )

    mass32 = float(
        np.sum(
            result32,
            dtype=np.float64,
        )
    )

    relative_mass_error = (
        abs(
            mass64
            - mass32
        )
        / abs(
            mass64
        )
    )

    mask64 = (
        result64
        >= args.threshold
    )

    mask32 = (
        result32
        >= args.threshold
    )

    threshold_dice = dice_score(
        mask32,
        mask64,
    )

    speedup = (
        elapsed64
        / elapsed32
    )

    print()
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)

    print(
        f"Speedup: {speedup:.3f}x"
    )

    print(
        f"Max absolute error: "
        f"{max_abs_error:.8e}"
    )

    print(
        f"Mean absolute error: "
        f"{mean_abs_error:.8e}"
    )

    print(
        f"Relative mass error: "
        f"{relative_mass_error:.8e}"
    )

    print(
        f"Threshold Dice: "
        f"{threshold_dice:.8f}"
    )

    print(
        "Threshold voxel disagreement: "
        f"{int(np.count_nonzero(mask64 != mask32))}"
    )


if __name__ == "__main__":
    main()