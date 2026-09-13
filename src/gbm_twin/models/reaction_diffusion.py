from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ReactionDiffusionParameters:
    diffusion: float
    proliferation: float

    def __post_init__(self) -> None:
        if self.diffusion < 0:
            raise ValueError("diffusion must be non-negative")

        if self.proliferation < 0:
            raise ValueError("proliferation must be non-negative")


def gaussian_initial_condition(
    shape: tuple[int, int, int],
    *,
    center: tuple[float, float, float] | None = None,
    sigma: float = 3.0,
) -> np.ndarray:
    if sigma <= 0:
        raise ValueError("sigma must be positive")

    if center is None:
        resolved_center = (
            (shape[0] - 1) / 2,
            (shape[1] - 1) / 2,
            (shape[2] - 1) / 2,
        )
    else:
        resolved_center = center

    x, y, z = np.indices(shape, dtype=float)

    distance_squared = (
        (x - resolved_center[0]) ** 2
        + (y - resolved_center[1]) ** 2
        + (z - resolved_center[2]) ** 2
    )

    concentration = np.exp(
        -distance_squared / (2.0 * sigma**2)
    )

    return concentration