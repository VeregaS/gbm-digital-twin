import numpy as np

from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters


def laplacian_3d(
    field: np.ndarray,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    if field.ndim != 3:
        raise ValueError(f"Expected 3D field, got shape {field.shape}")

    if any(value <= 0 for value in spacing):
        raise ValueError("Spacing values must be positive")

    dx, dy, dz = spacing

    padded = np.pad(
        field,
        pad_width=1,
        mode="edge",
    )

    center = padded[1:-1, 1:-1, 1:-1]

    d2x = (
        padded[2:, 1:-1, 1:-1]
        - 2.0 * center
        + padded[:-2, 1:-1, 1:-1]
    ) / dx**2

    d2y = (
        padded[1:-1, 2:, 1:-1]
        - 2.0 * center
        + padded[1:-1, :-2, 1:-1]
    ) / dy**2

    d2z = (
        padded[1:-1, 1:-1, 2:]
        - 2.0 * center
        + padded[1:-1, 1:-1, :-2]
    ) / dz**2

    return d2x + d2y + d2z

def explicit_stability_limit(
    diffusion: float,
    spacing: tuple[float, float, float],
) -> float:
    if diffusion <= 0:
        return float("inf")

    dx, dy, dz = spacing

    return 1.0 / (
        2.0
        * diffusion
        * (
            1.0 / dx**2
            + 1.0 / dy**2
            + 1.0 / dz**2
        )
    )


def reaction_diffusion_step(
    field: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    dt: float,
) -> np.ndarray:
    if dt <= 0:
        raise ValueError("dt must be positive")

    stability_limit = explicit_stability_limit(
        params.diffusion,
        spacing,
    )

    if dt > stability_limit:
        raise ValueError(
            f"dt={dt} exceeds explicit diffusion stability limit "
            f"{stability_limit:.6g}"
        )

    diffusion_term = params.diffusion * laplacian_3d(
        field,
        spacing,
    )

    reaction_term = (
        params.proliferation
        * field
        * (1.0 - field)
    )

    return field + dt * (
        diffusion_term + reaction_term
    )