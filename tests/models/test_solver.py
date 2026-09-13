import numpy as np

from gbm_twin.models.solver import laplacian_3d


def test_constant_field_has_zero_laplacian() -> None:
    field = np.ones((7, 7, 7), dtype=float)

    result = laplacian_3d(
        field,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.allclose(result, 0.0)


def test_impulse_laplacian_center() -> None:
    field = np.zeros((7, 7, 7), dtype=float)
    field[3, 3, 3] = 1.0

    result = laplacian_3d(
        field,
        spacing=(1.0, 1.0, 1.0),
    )

    assert np.isclose(result[3, 3, 3], -6.0)

    assert np.isclose(result[2, 3, 3], 1.0)
    assert np.isclose(result[4, 3, 3], 1.0)
    assert np.isclose(result[3, 2, 3], 1.0)
    assert np.isclose(result[3, 4, 3], 1.0)
    assert np.isclose(result[3, 3, 2], 1.0)
    assert np.isclose(result[3, 3, 4], 1.0)