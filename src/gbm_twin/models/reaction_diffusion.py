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

def initial_condition_from_gtv(
    gtv: np.ndarray,
    domain_mask: np.ndarray,
    *,
    threshold: float = 0.5,
) -> np.ndarray:
    if gtv.ndim != 3 or domain_mask.ndim != 3:
        raise ValueError("GTV and domain mask must be 3D")

    if gtv.shape != domain_mask.shape:
        raise ValueError(
            f"Shape mismatch: GTV {gtv.shape}, domain {domain_mask.shape}"
        )

    tumor = gtv > threshold
    domain = domain_mask > threshold

    if not np.any(tumor):
        raise ValueError("GTV mask is empty")

    if np.any(tumor & ~domain):
        raise ValueError("GTV must be fully contained in computational domain")

    field = np.zeros(gtv.shape, dtype=float)
    field[tumor] = 1.0

    return field

def build_computational_domain(
    brain_mask: np.ndarray,
    gtv: np.ndarray,
    *,
    threshold: float = 0.5,
) -> np.ndarray:
    if brain_mask.ndim != 3 or gtv.ndim != 3:
        raise ValueError("Brain mask and GTV must be 3D")

    if brain_mask.shape != gtv.shape:
        raise ValueError(
            f"Shape mismatch: brain {brain_mask.shape}, GTV {gtv.shape}"
        )

    brain = brain_mask > threshold
    tumor = gtv > threshold

    if not np.any(brain):
        raise ValueError("Brain mask is empty")

    if not np.any(tumor):
        raise ValueError("GTV mask is empty")

    return brain | tumor