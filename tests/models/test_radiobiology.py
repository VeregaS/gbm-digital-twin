import pytest

from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)


def test_beta_is_derived_from_alpha_beta_ratio() -> None:
    parameters = RadiobiologyParameters(
        alpha_per_gy=0.1,
        alpha_beta_ratio_gy=10.0,
    )

    assert (
        parameters.beta_per_gy2
        == pytest.approx(0.01)
    )


def test_zero_alpha_is_allowed() -> None:
    parameters = RadiobiologyParameters(
        alpha_per_gy=0.0,
        alpha_beta_ratio_gy=10.0,
    )

    assert (
        parameters.beta_per_gy2
        == 0.0
    )


def test_rejects_negative_alpha() -> None:
    with pytest.raises(
        ValueError,
        match="Alpha",
    ):
        RadiobiologyParameters(
            alpha_per_gy=-0.1,
            alpha_beta_ratio_gy=10.0,
        )


def test_rejects_zero_alpha_beta_ratio() -> None:
    with pytest.raises(
        ValueError,
        match="Alpha/beta",
    ):
        RadiobiologyParameters(
            alpha_per_gy=0.1,
            alpha_beta_ratio_gy=0.0,
        )


def test_rejects_negative_alpha_beta_ratio() -> None:
    with pytest.raises(
        ValueError,
        match="Alpha/beta",
    ):
        RadiobiologyParameters(
            alpha_per_gy=0.1,
            alpha_beta_ratio_gy=-10.0,
        )