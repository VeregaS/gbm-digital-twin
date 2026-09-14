import time
from concurrent.futures import (
    ProcessPoolExecutor,
)

import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)

_INITIAL_FIELD: np.ndarray | None = None
_DOMAIN_MASK: np.ndarray | None = None
_SPACING: tuple[float, float, float] | None = None
_DURATION_DAYS: float | None = None
_DT: float | None = None


CANDIDATES = [
    (0.005, 0.025),
    (0.005, 0.035),
    (0.010, 0.035),
    (0.010, 0.045),
    (0.015, 0.035),
    (0.015, 0.045),
]


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


def initialize_worker(
    initial_field: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
) -> None:
    global _INITIAL_FIELD
    global _DOMAIN_MASK
    global _SPACING
    global _DURATION_DAYS
    global _DT

    _INITIAL_FIELD = initial_field
    _DOMAIN_MASK = domain_mask
    _SPACING = spacing
    _DURATION_DAYS = duration_days
    _DT = dt


def run_candidate(
    candidate: tuple[
        float,
        float,
    ],
) -> tuple[
    float,
    float,
    float,
    float,
]:
    if _INITIAL_FIELD is None:
        raise RuntimeError(
            "Worker initial field is not initialized"
        )

    if _DOMAIN_MASK is None:
        raise RuntimeError(
            "Worker domain mask is not initialized"
        )

    if _SPACING is None:
        raise RuntimeError(
            "Worker spacing is not initialized"
        )

    if _DURATION_DAYS is None:
        raise RuntimeError(
            "Worker duration is not initialized"
        )

    if _DT is None:
        raise RuntimeError(
            "Worker dt is not initialized"
        )

    diffusion, proliferation = (
        candidate
    )

    params = ReactionDiffusionParameters(
        diffusion=diffusion,
        proliferation=proliferation,
    )

    result = simulate_reaction_diffusion(
        _INITIAL_FIELD,
        params,
        spacing=_SPACING,
        duration_days=_DURATION_DAYS,
        dt=_DT,
        domain_mask=_DOMAIN_MASK,
        crop_to_domain=True,
    )

    return (
        diffusion,
        proliferation,
        float(
            np.sum(
                result,
                dtype=np.float64,
            )
        ),
        float(
            np.max(
                result
            )
        ),
    )


def run_sequential(
    initial_field: np.ndarray,
    domain_mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
) -> tuple[
    list[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ],
    float,
]:
    initialize_worker(
        initial_field,
        domain_mask,
        spacing,
        duration_days,
        dt,
    )

    started = time.perf_counter()

    results = [
        run_candidate(
            candidate
        )
        for candidate in CANDIDATES
    ]

    elapsed = (
        time.perf_counter()
        - started
    )

    return (
        results,
        elapsed,
    )


def run_parallel(
    initial_field: np.ndarray,
    domain_mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    workers: int,
) -> tuple[
    list[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ],
    float,
]:
    started = time.perf_counter()

    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=initialize_worker,
        initargs=(
            initial_field,
            domain_mask,
            spacing,
            duration_days,
            dt,
        ),
    ) as executor:
        results = list(
            executor.map(
                run_candidate,
                CANDIDATES,
            )
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    return (
        results,
        elapsed,
    )


def compare_results(
    sequential: list[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ],
    parallel: list[
        tuple[
            float,
            float,
            float,
            float,
        ]
    ],
) -> tuple[
    float,
    float,
]:
    sequential_sorted = sorted(
        sequential
    )

    parallel_sorted = sorted(
        parallel
    )

    if len(
        sequential_sorted
    ) != len(
        parallel_sorted
    ):
        raise RuntimeError(
            "Result count mismatch"
        )

    max_mass_error = 0.0
    max_field_max_error = 0.0

    for left, right in zip(
        sequential_sorted,
        parallel_sorted,
        strict=True,
    ):
        if (
            left[0]
            != right[0]
            or left[1]
            != right[1]
        ):
            raise RuntimeError(
                "Candidate mismatch"
            )

        max_mass_error = max(
            max_mass_error,
            abs(
                left[2]
                - right[2]
            ),
        )

        max_field_max_error = max(
            max_field_max_error,
            abs(
                left[3]
                - right[3]
            ),
        )

    return (
        max_mass_error,
        max_field_max_error,
    )


def main() -> None:
    initial_field, domain_mask = (
        build_case()
    )

    spacing = (
        2.0,
        2.0,
        2.0,
    )

    duration_days = 168.0
    dt = 2.0

    print()
    print("=" * 60)
    print("SEQUENTIAL: 1 WORKER")
    print("=" * 60)

    sequential, sequential_time = (
        run_sequential(
            initial_field,
            domain_mask,
            spacing=spacing,
            duration_days=duration_days,
            dt=dt,
        )
    )

    print(
        f"Candidates: {len(CANDIDATES)}"
    )

    print(
        f"Elapsed: {sequential_time:.3f} s"
    )

    print(
        "Time / candidate: "
        f"{sequential_time / len(CANDIDATES):.3f} s"
    )

    print()
    print("=" * 60)
    print("PARALLEL: 2 WORKERS")
    print("=" * 60)

    parallel, parallel_time = (
        run_parallel(
            initial_field,
            domain_mask,
            spacing=spacing,
            duration_days=duration_days,
            dt=dt,
            workers=2,
        )
    )

    print(
        f"Candidates: {len(CANDIDATES)}"
    )

    print(
        f"Elapsed: {parallel_time:.3f} s"
    )

    print(
        "Effective time / candidate: "
        f"{parallel_time / len(CANDIDATES):.3f} s"
    )

    speedup = (
        sequential_time
        / parallel_time
    )

    (
        max_mass_error,
        max_field_max_error,
    ) = compare_results(
        sequential,
        parallel,
    )

    print()
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)

    print(
        f"Speedup: {speedup:.3f}x"
    )

    print(
        f"Parallel efficiency: "
        f"{speedup / 2.0:.1%}"
    )

    print(
        f"Max mass error: "
        f"{max_mass_error:.8e}"
    )

    print(
        f"Max concentration error: "
        f"{max_field_max_error:.8e}"
    )


if __name__ == "__main__":
    main()