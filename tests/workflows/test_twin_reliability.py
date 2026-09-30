from __future__ import annotations

import numpy as np

from gbm_twin.workflows.twin_reliability import (
    assess_forecast_reliability,
)


def _base_kwargs(
) -> dict[
    str,
    object,
]:
    mask = np.zeros(
        (
            5,
            5,
            5,
        ),
        dtype=np.uint8,
    )

    mask[
        1:4,
        1:4,
        1:4,
    ] = 1

    return {
        "patient_id": 42,
        "model_version": "V2",
        "protocol_version": (
            "v2-frozen-1"
        ),
        "sealed": True,
        "source_git_commit_sha": (
            "a" * 40
        ),
        "source_git_dirty": False,
        "forecast_horizon_days": 90.0,
        "calibration_identifiable": True,
        "diffusion_at_boundary": False,
        "proliferation_at_boundary": False,
        "prediction_mask": mask,
        "brain_mask": np.ones_like(
            mask
        ),
    }


def test_nominal_reliability_has_no_pre_t2_flags(
) -> None:
    report = (
        assess_forecast_reliability(
            **_base_kwargs(),
        )
    )

    assert (
        report.status
        == "nominal"
    )

    assert report.factors == ()


def test_non_identifiable_calibration_is_limited(
) -> None:
    kwargs = _base_kwargs()

    kwargs[
        "calibration_identifiable"
    ] = False

    report = (
        assess_forecast_reliability(
            **kwargs,
        )
    )

    assert (
        report.status
        == "limited"
    )

    assert (
        "calibration_non_identifiable"
        in {
            factor.code
            for factor in report.factors
        }
    )


def test_boundary_only_is_caution(
) -> None:
    kwargs = _base_kwargs()

    kwargs[
        "diffusion_at_boundary"
    ] = True

    report = (
        assess_forecast_reliability(
            **kwargs,
        )
    )

    assert (
        report.status
        == "caution"
    )


def test_prediction_outside_t1_brain_is_limited(
) -> None:
    kwargs = _base_kwargs()

    prediction = np.asarray(
        kwargs[
            "prediction_mask"
        ]
    ).copy()

    brain = np.asarray(
        kwargs[
            "brain_mask"
        ]
    ).copy()

    brain[
        1,
        1,
        1,
    ] = 0

    kwargs[
        "prediction_mask"
    ] = prediction

    kwargs[
        "brain_mask"
    ] = brain

    report = (
        assess_forecast_reliability(
            **kwargs,
        )
    )

    assert (
        report.status
        == "limited"
    )

    assert (
        report
        .prediction_outside_brain_fraction
        is not None
    )

    assert (
        report
        .prediction_outside_brain_fraction
        > 0.001
    )
