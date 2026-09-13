import pandas as pd
import pytest

from gbm_twin.evaluation.analysis import (
    analyze_results,
    classify_volume_trajectory,
)


@pytest.mark.parametrize(
    (
        "relative_change",
        "expected",
    ),
    [
        (0.50, "growth"),
        (0.11, "growth"),
        (0.10, "stable"),
        (0.05, "stable"),
        (0.00, "stable"),
        (-0.05, "stable"),
        (-0.10, "stable"),
        (-0.11, "regression"),
        (-0.50, "regression"),
    ],
)
def test_classify_volume_trajectory(
    relative_change: float,
    expected: str,
) -> None:
    result = classify_volume_trajectory(
        relative_change,
        stable_threshold=0.10,
    )

    assert result == expected


def test_classify_volume_trajectory_rejects_negative_threshold() -> None:
    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        classify_volume_trajectory(
            0.0,
            stable_threshold=-0.1,
        )


def test_analyze_results() -> None:
    raw = pd.DataFrame(
        [
            {
                "patient_id": 1,
                "volume_t0_cm3": 10.0,
                "volume_t1_cm3": 12.0,
                "volume_t2_cm3": 12.6,
                "twin_dice": 0.80,
                "twin_volume_error": 0.10,
                "persistence_dice": 0.70,
                "persistence_volume_error": 0.20,
                "morphological_dice": 0.75,
                "morphological_volume_error": 0.15,
            },
            {
                "patient_id": 2,
                "volume_t0_cm3": 10.0,
                "volume_t1_cm3": 8.0,
                "volume_t2_cm3": 7.0,
                "twin_dice": 0.60,
                "twin_volume_error": 0.30,
                "persistence_dice": 0.65,
                "persistence_volume_error": 0.25,
                "morphological_dice": 0.62,
                "morphological_volume_error": 0.28,
            },
        ]
    )

    analyzed = analyze_results(
        raw,
        stable_threshold=0.10,
    )

    first = analyzed.iloc[0]
    second = analyzed.iloc[1]

    assert first["trajectory_t0_t1"] == "growth"
    assert first["trajectory_t1_t2"] == "stable"
    assert bool(
        first["calibration_compatible"]
    )
    assert bool(
        first["twin_beats_persistence"]
    )

    assert second[
        "trajectory_t0_t1"
    ] == "regression"

    assert second[
        "trajectory_t1_t2"
    ] == "regression"

    assert not bool(
        second[
            "calibration_compatible"
        ]
    )

    assert not bool(
        second[
            "twin_beats_persistence"
        ]
    )