import numpy as np
import pytest

from gbm_twin.evaluation.soft_metrics import (
    soft_dice_score,
    soft_relative_volume_error,
    soft_threshold_membership,
)


def test_soft_threshold_is_half_at_threshold() -> None:
    field = np.asarray(
        [0.5],
        dtype=np.float32,
    )

    result = soft_threshold_membership(
        field,
        threshold=0.5,
        temperature=0.05,
    )

    assert result[0] == pytest.approx(
        0.5
    )


def test_soft_threshold_zeroes_outside_domain() -> None:
    field = np.asarray(
        [
            1.0,
            1.0,
        ],
        dtype=np.float32,
    )

    domain = np.asarray(
        [
            True,
            False,
        ],
        dtype=bool,
    )

    result = soft_threshold_membership(
        field,
        threshold=0.5,
        temperature=0.05,
        domain_mask=domain,
    )

    assert result[0] > 0.99
    assert result[1] == 0.0


def test_soft_dice_distinguishes_subthreshold_fields() -> None:
    observed = np.asarray(
        [
            True,
            False,
        ],
        dtype=bool,
    )

    low = soft_threshold_membership(
        np.asarray(
            [
                0.10,
                0.0,
            ],
            dtype=np.float32,
        ),
        threshold=0.5,
        temperature=0.05,
    )

    near = soft_threshold_membership(
        np.asarray(
            [
                0.49,
                0.0,
            ],
            dtype=np.float32,
        ),
        threshold=0.5,
        temperature=0.05,
    )

    assert soft_dice_score(
        near,
        observed,
    ) > soft_dice_score(
        low,
        observed,
    )


def test_soft_volume_error_prefers_correct_mass() -> None:
    observed = np.asarray(
        [
            True,
            False,
        ],
        dtype=bool,
    )

    good = np.asarray(
        [
            0.9,
            0.1,
        ],
        dtype=np.float64,
    )

    bad = np.asarray(
        [
            0.2,
            0.1,
        ],
        dtype=np.float64,
    )

    assert soft_relative_volume_error(
        good,
        observed,
    ) < soft_relative_volume_error(
        bad,
        observed,
    )