import numpy as np


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