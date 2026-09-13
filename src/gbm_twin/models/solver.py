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
    params: ReactionDiffusionParameters,
    spacing: tuple[float, float, float],
) -> float:
    dx, dy, dz = spacing

    diffusion_rate = (
        2.0
        * params.diffusion
        * (
            1.0 / dx**2
            + 1.0 / dy**2
            + 1.0 / dz**2
        )
    )

    total_rate = diffusion_rate + params.proliferation

    if total_rate == 0:
        return float("inf")

    return 1.0 / total_rate


def reaction_diffusion_step(
    field: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    dt: float,
    domain_mask: np.ndarray | None = None,
) -> np.ndarray:
    if dt <= 0:
        raise ValueError("dt must be positive")

    stability_limit = explicit_stability_limit(
        params,
        spacing,
    )

    if dt > stability_limit:
        raise ValueError(
            f"dt={dt} exceeds explicit diffusion stability limit "
            f"{stability_limit:.6g}"
        )

    if domain_mask is None:
        laplacian = laplacian_3d(
            field,
            spacing,
        )
        active_field = field
    else:
        if domain_mask.shape != field.shape:
            raise ValueError(
                f"Domain mask shape {domain_mask.shape} "
                f"does not match field shape {field.shape}"
            )

        active_field = np.where(domain_mask, field, 0.0)

        laplacian = masked_laplacian_3d(
            active_field,
            domain_mask,
            spacing,
        )

    diffusion_term = params.diffusion * laplacian

    reaction_term = (
        params.proliferation
        * active_field
        * (1.0 - active_field)
    )

    result = active_field + dt * (
        diffusion_term + reaction_term
    )

    if domain_mask is not None:
        result[~domain_mask.astype(bool)] = 0.0

    return result
    
def simulate_reaction_diffusion(
    initial_field: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    domain_mask: np.ndarray | None = None,
) -> np.ndarray:
    if duration_days < 0:
        raise ValueError("duration_days must be non-negative")

    if dt <= 0:
        raise ValueError("dt must be positive")

    field = np.asarray(initial_field, dtype=float).copy()

    if field.ndim != 3:
        raise ValueError(
            f"Expected 3D initial field, got shape {field.shape}"
        )

    if np.any(field < 0) or np.any(field > 1):
        raise ValueError(
            "Initial concentration must be within [0, 1]"
        )

    remaining_time = duration_days

    while remaining_time > 0:
        step_dt = min(dt, remaining_time)

        field = reaction_diffusion_step(
            field,
            params,
            spacing=spacing,
            dt=step_dt,
            domain_mask=domain_mask,
        )

        remaining_time -= step_dt

    return field

def masked_laplacian_3d(
    field: np.ndarray,
    mask: np.ndarray,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    if field.ndim != 3:
        raise ValueError(f"Expected 3D field, got shape {field.shape}")

    if mask.shape != field.shape:
        raise ValueError(
            f"Mask shape {mask.shape} does not match field shape {field.shape}"
        )

    if any(value <= 0 for value in spacing):
        raise ValueError("Spacing values must be positive")

    mask = mask.astype(bool)

    dx, dy, dz = spacing

    padded_field = np.pad(
        field,
        pad_width=1,
        mode="constant",
        constant_values=0,
    )

    padded_mask = np.pad(
        mask,
        pad_width=1,
        mode="constant",
        constant_values=False,
    )

    center = padded_field[1:-1, 1:-1, 1:-1]

    x_plus = np.where(
        padded_mask[2:, 1:-1, 1:-1],
        padded_field[2:, 1:-1, 1:-1],
        center,
    )
    x_minus = np.where(
        padded_mask[:-2, 1:-1, 1:-1],
        padded_field[:-2, 1:-1, 1:-1],
        center,
    )

    y_plus = np.where(
        padded_mask[1:-1, 2:, 1:-1],
        padded_field[1:-1, 2:, 1:-1],
        center,
    )
    y_minus = np.where(
        padded_mask[1:-1, :-2, 1:-1],
        padded_field[1:-1, :-2, 1:-1],
        center,
    )

    z_plus = np.where(
        padded_mask[1:-1, 1:-1, 2:],
        padded_field[1:-1, 1:-1, 2:],
        center,
    )
    z_minus = np.where(
        padded_mask[1:-1, 1:-1, :-2],
        padded_field[1:-1, 1:-1, :-2],
        center,
    )

    result = (
        (x_plus - 2.0 * center + x_minus) / dx**2
        + (y_plus - 2.0 * center + y_minus) / dy**2
        + (z_plus - 2.0 * center + z_minus) / dz**2
    )

    result[~mask] = 0.0

    return result