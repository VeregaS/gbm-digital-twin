import math

import pytest

from gbm_twin.workflows.contracts import PredictionTarget


def test_prediction_target_normalizes_values() -> None:
    target = PredictionTarget(
        timepoint_name="  t2  ",
        target_day=120,
    )

    assert target.timepoint_name == "t2"
    assert target.target_day == 120.0


def test_prediction_target_rejects_empty_timepoint() -> None:
    with pytest.raises(
        ValueError,
        match="must not be empty",
    ):
        PredictionTarget(
            timepoint_name="   ",
            target_day=120.0,
        )


@pytest.mark.parametrize(
    "target_day",
    (
        math.nan,
        math.inf,
        -math.inf,
    ),
)
def test_prediction_target_rejects_non_finite_day(
    target_day: float,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        PredictionTarget(
            timepoint_name="t2",
            target_day=target_day,
        )