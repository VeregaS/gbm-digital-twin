import numpy as np
import pytest

from gbm_twin.models.pirt import (
    apply_pirt_fraction,
    pirt_radiation_loss,
)


def test_pirt_loss_matches_formula() -> None:
    field = np.array(
        [
            0.0,
            0.25,
            0.50,
            0.75,
            1.0,
        ],
        dtype=np.float64,
    ).reshape(
        5,
        1,
        1,
    )

    survival = 0.8

    loss = pirt_radiation_loss(
        field,
        survival_fraction=survival,
    )

    expected = (
        (1.0 - survival)
        * field
        * (1.0 - field)
    )

    np.testing.assert_allclose(
        loss,
        expected,
    )


def test_pirt_fraction_matches_expected_values() -> None:
    field = np.array(
        [
            0.0,
            0.25,
            0.50,
            0.75,
            1.0,
        ],
        dtype=np.float64,
    ).reshape(
        5,
        1,
        1,
    )

    result = apply_pirt_fraction(
        field,
        survival_fraction=0.8,
    )

    expected = np.array(
        [
            0.0,
            0.2125,
            0.45,
            0.7125,
            1.0,
        ],
        dtype=np.float64,
    ).reshape(
        5,
        1,
        1,
    )

    np.testing.assert_allclose(
        result,
        expected,
    )


def test_pirt_preserves_zero_and_saturated_state() -> None:
    field = np.array(
        [
            0.0,
            1.0,
        ],
        dtype=np.float64,
    ).reshape(
        2,
        1,
        1,
    )

    result = apply_pirt_fraction(
        field,
        survival_fraction=0.1,
    )

    np.testing.assert_array_equal(
        result,
        field,
    )


def test_pirt_is_not_plain_multiplicative_kill() -> None:
    field = np.ones(
        (3, 3, 3),
        dtype=np.float64,
    )

    survival = 0.8

    pirt = apply_pirt_fraction(
        field,
        survival_fraction=survival,
    )

    multiplicative = (
        field
        * survival
    )

    np.testing.assert_array_equal(
        pirt,
        field,
    )

    assert not np.array_equal(
        pirt,
        multiplicative,
    )


def test_pirt_respects_domain_mask() -> None:
    field = np.full(
        (3, 3, 3),
        0.5,
        dtype=np.float64,
    )

    domain = np.zeros(
        field.shape,
        dtype=bool,
    )

    domain[
        1,
        1,
        1,
    ] = True

    result = apply_pirt_fraction(
        field,
        survival_fraction=0.8,
        domain_mask=domain,
    )

    assert result[
        1,
        1,
        1,
    ] < 0.5

    outside = ~domain

    np.testing.assert_array_equal(
        result[outside],
        field[outside],
    )


def test_pirt_preserves_float32() -> None:
    field = np.full(
        (3, 3, 3),
        0.5,
        dtype=np.float32,
    )

    result = apply_pirt_fraction(
        field,
        survival_fraction=0.8,
    )

    assert (
        result.dtype
        == np.float32
    )


@pytest.mark.parametrize(
    "survival_fraction",
    [
        -0.1,
        1.1,
        float("nan"),
        float("inf"),
    ],
)
def test_pirt_rejects_invalid_survival_fraction(
    survival_fraction: float,
) -> None:
    field = np.full(
        (3, 3, 3),
        0.5,
        dtype=np.float64,
    )

    with pytest.raises(
        ValueError,
        match="survival_fraction",
    ):
        apply_pirt_fraction(
            field,
            survival_fraction=survival_fraction,
        )


def test_pirt_rejects_invalid_field_range() -> None:
    field = np.full(
        (3, 3, 3),
        1.1,
        dtype=np.float64,
    )

    with pytest.raises(
        ValueError,
        match=r"\[0, 1\]",
    ):
        apply_pirt_fraction(
            field,
            survival_fraction=0.8,
        )


def test_pirt_rejects_domain_shape_mismatch() -> None:
    field = np.full(
        (3, 3, 3),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        (2, 2, 2),
        dtype=bool,
    )

    with pytest.raises(
        ValueError,
        match="domain_mask",
    ):
        apply_pirt_fraction(
            field,
            survival_fraction=0.8,
            domain_mask=domain,
        )