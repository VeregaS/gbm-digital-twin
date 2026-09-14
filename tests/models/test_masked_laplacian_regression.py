import numpy as np

from gbm_twin.models.solver import (
    masked_laplacian_3d,
)


def reference_masked_laplacian(
    field: np.ndarray,
    mask: np.ndarray,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    domain = np.asarray(
        mask,
        dtype=bool,
    )

    padded_field = np.pad(
        field,
        pad_width=1,
        mode="constant",
        constant_values=0,
    )

    padded_mask = np.pad(
        domain,
        pad_width=1,
        mode="constant",
        constant_values=False,
    )

    center = padded_field[
        1:-1,
        1:-1,
        1:-1,
    ]

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

    dx, dy, dz = spacing

    result = (
        (
            x_plus
            - 2.0 * center
            + x_minus
        )
        / dx**2
        + (
            y_plus
            - 2.0 * center
            + y_minus
        )
        / dy**2
        + (
            z_plus
            - 2.0 * center
            + z_minus
        )
        / dz**2
    )

    result[
        ~domain
    ] = 0.0

    return result


def test_optimized_laplacian_matches_reference() -> None:
    rng = np.random.default_rng(
        12345
    )

    field = rng.random(
        (17, 19, 13)
    )

    mask = (
        rng.random(
            field.shape
        )
        > 0.25
    )

    spacing = (
        1.5,
        2.0,
        2.5,
    )

    expected = (
        reference_masked_laplacian(
            field,
            mask,
            spacing,
        )
    )

    actual = masked_laplacian_3d(
        field,
        mask,
        spacing,
    )

    np.testing.assert_allclose(
        actual,
        expected,
        rtol=1e-12,
        atol=1e-12,
    )


def test_masked_laplacian_conserves_flux() -> None:
    rng = np.random.default_rng(
        54321
    )

    field = rng.random(
        (15, 16, 17)
    )

    mask = (
        rng.random(
            field.shape
        )
        > 0.3
    )

    result = masked_laplacian_3d(
        field,
        mask,
        (
            2.0,
            2.0,
            2.0,
        ),
    )

    assert np.isclose(
        np.sum(result),
        0.0,
        atol=1e-12,
    )


def test_masked_laplacian_is_zero_outside_domain() -> None:
    field = np.ones(
        (7, 7, 7),
        dtype=float,
    )

    mask = np.zeros(
        field.shape,
        dtype=bool,
    )

    mask[
        2:5,
        2:5,
        2:5,
    ] = True

    result = masked_laplacian_3d(
        field,
        mask,
        (
            1.0,
            1.0,
            1.0,
        ),
    )

    assert np.all(
        result[
            ~mask
        ]
        == 0.0
    )