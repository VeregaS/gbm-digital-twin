import pytest

from gbm_twin.calibration.diagnostics import (
    assess_calibration_diagnostics,
)
from gbm_twin.calibration.grid_search import (
    CalibrationResult,
)


def make_result(
    *,
    diffusion: float,
    proliferation: float,
    loss: float,
) -> CalibrationResult:
    return CalibrationResult(
        diffusion=diffusion,
        proliferation=proliferation,
        dice=1.0 - loss,
        volume_error=0.0,
        loss=loss,
    )


def test_interior_unique_optimum_is_identifiable() -> None:
    candidates = (
        make_result(
            diffusion=0.01,
            proliferation=0.01,
            loss=0.3,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.01,
            loss=0.2,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.01,
            loss=0.3,
        ),
        make_result(
            diffusion=0.01,
            proliferation=0.02,
            loss=0.2,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.02,
            loss=0.1,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.02,
            loss=0.2,
        ),
        make_result(
            diffusion=0.01,
            proliferation=0.03,
            loss=0.3,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.03,
            loss=0.2,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.03,
            loss=0.3,
        ),
    )

    best = candidates[4]

    diagnostics = (
        assess_calibration_diagnostics(
            best=best,
            candidates=candidates,
        )
    )

    assert not diagnostics.diffusion_at_boundary
    assert not diagnostics.proliferation_at_boundary

    assert diagnostics.diffusion_bracketed
    assert diagnostics.proliferation_bracketed
    assert diagnostics.identifiable


def test_boundary_optimum_is_not_identifiable() -> None:
    candidates = (
        make_result(
            diffusion=0.01,
            proliferation=0.01,
            loss=0.3,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.01,
            loss=0.2,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.01,
            loss=0.1,
        ),
        make_result(
            diffusion=0.01,
            proliferation=0.02,
            loss=0.4,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.02,
            loss=0.3,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.02,
            loss=0.2,
        ),
    )

    best = candidates[2]

    diagnostics = (
        assess_calibration_diagnostics(
            best=best,
            candidates=candidates,
        )
    )

    assert diagnostics.diffusion_at_boundary
    assert not diagnostics.diffusion_bracketed

    assert diagnostics.proliferation_at_boundary
    assert not diagnostics.proliferation_bracketed

    assert not diagnostics.identifiable


def test_tied_distinct_optima_are_not_identifiable() -> None:
    candidates = (
        make_result(
            diffusion=0.01,
            proliferation=0.01,
            loss=0.3,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.01,
            loss=0.2,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.01,
            loss=0.3,
        ),
        make_result(
            diffusion=0.01,
            proliferation=0.02,
            loss=0.2,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.02,
            loss=0.1,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.02,
            loss=0.1,
        ),
        make_result(
            diffusion=0.01,
            proliferation=0.03,
            loss=0.3,
        ),
        make_result(
            diffusion=0.02,
            proliferation=0.03,
            loss=0.2,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.03,
            loss=0.3,
        ),
    )

    best = candidates[4]

    diagnostics = (
        assess_calibration_diagnostics(
            best=best,
            candidates=candidates,
        )
    )

    assert diagnostics.diffusion_bracketed
    assert diagnostics.proliferation_bracketed

    assert not diagnostics.identifiable


def test_duplicate_same_parameter_pair_does_not_create_false_tie() -> None:
    best = make_result(
        diffusion=0.02,
        proliferation=0.02,
        loss=0.1,
    )

    candidates = (
        make_result(
            diffusion=0.01,
            proliferation=0.01,
            loss=0.3,
        ),
        best,
        make_result(
            diffusion=0.02,
            proliferation=0.02,
            loss=0.1,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.03,
            loss=0.3,
        ),
    )

    diagnostics = (
        assess_calibration_diagnostics(
            best=best,
            candidates=candidates,
        )
    )

    assert diagnostics.diffusion_bracketed
    assert diagnostics.proliferation_bracketed
    assert diagnostics.identifiable


def test_diagnostics_reject_empty_candidates() -> None:
    best = make_result(
        diffusion=0.02,
        proliferation=0.02,
        loss=0.1,
    )

    with pytest.raises(
        ValueError,
        match="at least one candidate",
    ):
        assess_calibration_diagnostics(
            best=best,
            candidates=(),
        )


def test_diagnostics_reject_best_outside_candidates() -> None:
    best = make_result(
        diffusion=0.02,
        proliferation=0.02,
        loss=0.1,
    )

    candidates = (
        make_result(
            diffusion=0.01,
            proliferation=0.01,
            loss=0.2,
        ),
        make_result(
            diffusion=0.03,
            proliferation=0.03,
            loss=0.3,
        ),
    )

    with pytest.raises(
        ValueError,
        match="must be present",
    ):
        assess_calibration_diagnostics(
            best=best,
            candidates=candidates,
        )