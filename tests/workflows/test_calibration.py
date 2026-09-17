from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.calibration as calibration_module
from gbm_twin.calibration.grid_search import (
    CalibrationObjective,
    CalibrationResult,
)
from gbm_twin.calibration.refinement import (
    AdaptiveCalibrationResult,
)
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.models.latent_state import (
    LatentStateParameters,
)
from gbm_twin.models.solver import TreatmentModel
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    calibrate_v2_interval,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)


@dataclass
class CapturedCalibrationCall:
    duration_days: float | None = None
    start_time_day: float | None = None
    objective: CalibrationObjective | None = None
    soft_temperature: float | None = None
    refinement_rounds: int | None = None
    upper_boundary_expansion_factor: float | None = None


def make_volume(
    name: str,
) -> NiftiVolume:
    data = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    data[2, 2, 2] = 1.0

    return NiftiVolume(
        path=Path(name),
        data=data,
        affine=np.eye(
            4,
            dtype=np.float64,
        ),
        spacing=(
            2.0,
            2.0,
            2.0,
        ),
    )


def make_timepoint(
    *,
    name: str,
    day: float,
) -> PreparedPatientTimepoint:
    return PreparedPatientTimepoint(
        patient_id=42,
        name=name,
        days_from_baseline=day,
        t1gd=make_volume(
            f"{name}_t1gd.nii.gz"
        ),
        gtv=make_volume(
            f"{name}_gtv.nii.gz"
        ),
        brain_mask=make_volume(
            f"{name}_brain.nii.gz"
        ),
    )


def make_config() -> V2CalibrationConfig:
    return V2CalibrationConfig(
        diffusion_values=(
            0.0,
            0.03,
            0.06,
        ),
        proliferation_values=(
            0.0,
            0.015,
            0.03,
        ),
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


def test_calibrate_v2_interval_uses_only_interval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    start = make_timepoint(
        name="t0",
        day=0.0,
    )

    observed = make_timepoint(
        name="t1",
        day=77.0,
    )

    captured = CapturedCalibrationCall()

    def fake_latent_state_from_gtv(
        gtv_mask: np.ndarray,
        brain_mask: np.ndarray,
        *,
        spacing: tuple[
            float,
            float,
            float,
        ],
        parameters: LatentStateParameters,
    ) -> np.ndarray:
        assert (
            gtv_mask.shape
            == brain_mask.shape
        )

        assert spacing == (
            2.0,
            2.0,
            2.0,
        )

        assert (
            parameters.transition_width_mm
            > 0.0
        )

        return np.zeros(
            (5, 5, 5),
            dtype=np.float32,
        )

    monkeypatch.setattr(
        calibration_module,
        "latent_state_from_gtv",
        fake_latent_state_from_gtv,
    )

    expected = make_result(
        diffusion=0.03,
        proliferation=0.015,
        loss=0.1,
    )

    lower_diffusion = make_result(
        diffusion=0.015,
        proliferation=0.015,
        loss=0.2,
    )

    upper_diffusion = make_result(
        diffusion=0.045,
        proliferation=0.015,
        loss=0.2,
    )

    lower_proliferation = make_result(
        diffusion=0.03,
        proliferation=0.0075,
        loss=0.2,
    )

    upper_proliferation = make_result(
        diffusion=0.03,
        proliferation=0.0225,
        loss=0.2,
    )

    def fake_adaptive_grid_search(
        initial_field: np.ndarray,
        observed_mask: np.ndarray,
        domain_mask: np.ndarray,
        *,
        spacing: tuple[
            float,
            float,
            float,
        ],
        duration_days: float,
        dt: float,
        diffusion_values: list[float],
        proliferation_values: list[float],
        threshold: float,
        volume_weight: float,
        treatment: TreatmentModel | None,
        start_time_day: float,
        cache_dir: Path | None,
        workers: int,
        objective: CalibrationObjective,
        soft_temperature: float,
        refinement_rounds: int,
        upper_boundary_expansion_factor: float,
    ) -> AdaptiveCalibrationResult:
        captured.duration_days = (
            duration_days
        )

        captured.start_time_day = (
            start_time_day
        )

        captured.objective = objective

        captured.soft_temperature = (
            soft_temperature
        )

        captured.refinement_rounds = (
            refinement_rounds
        )

        captured.upper_boundary_expansion_factor = (
            upper_boundary_expansion_factor
        )

        assert initial_field.shape == (
            5,
            5,
            5,
        )

        assert observed_mask.shape == (
            5,
            5,
            5,
        )

        assert domain_mask.shape == (
            5,
            5,
            5,
        )

        assert spacing == (
            2.0,
            2.0,
            2.0,
        )

        assert dt == 2.0

        assert diffusion_values == [
            0.0,
            0.03,
            0.06,
        ]

        assert proliferation_values == [
            0.0,
            0.015,
            0.03,
        ]

        assert threshold == 0.5
        assert volume_weight == 0.5
        assert treatment is None
        assert cache_dir == tmp_path
        assert workers == 2
        assert refinement_rounds == 1
        assert upper_boundary_expansion_factor == 0.5

        return AdaptiveCalibrationResult(
            best=expected,
            coarse_best=expected,
            coarse_results=[
                expected,
            ],
            refined_results=[
                lower_diffusion,
                upper_diffusion,
                lower_proliferation,
                upper_proliferation,
            ],
            refined_diffusion_values=[
                0.015,
                0.03,
                0.045,
            ],
            refined_proliferation_values=[
                0.0075,
                0.015,
                0.0225,
            ],
        )

    monkeypatch.setattr(
        calibration_module,
        "adaptive_grid_search",
        fake_adaptive_grid_search,
    )

    result = calibrate_v2_interval(
        start=start,
        observed=observed,
        treatment=None,
        config=make_config(),
        cache_dir=tmp_path,
        workers=2,
    )

    assert result.patient_id == 42
    assert result.start_timepoint == "t0"
    assert result.observed_timepoint == "t1"
    assert result.duration_days == 77.0

    assert result.best == expected
    assert result.coarse_best == expected

    assert (
        result.refined_diffusion_values
        == (
            0.015,
            0.03,
            0.045,
        )
    )

    assert (
        result.refined_proliferation_values
        == (
            0.0075,
            0.015,
            0.0225,
        )
    )

    assert (
        not result
        .diagnostics
        .diffusion_at_boundary
    )

    assert (
        not result
        .diagnostics
        .proliferation_at_boundary
    )

    assert (
        result
        .diagnostics
        .diffusion_bracketed
    )

    assert (
        result
        .diagnostics
        .proliferation_bracketed
    )

    assert (
        result
        .diagnostics
        .identifiable
    )

    assert (
        captured.duration_days
        == 77.0
    )

    assert (
        captured.start_time_day
        == 0.0
    )

    assert (
        captured.objective
        == "soft"
    )

    assert (
        captured.soft_temperature
        == 0.05
    )

    assert (
        captured.refinement_rounds
        == 1
    )

    assert (
        captured.upper_boundary_expansion_factor
        == 0.5
    )


def test_calibrate_v2_interval_rejects_reverse_time(
    tmp_path: Path,
) -> None:
    start = make_timepoint(
        name="t1",
        day=77.0,
    )

    observed = make_timepoint(
        name="t0",
        day=0.0,
    )

    with pytest.raises(
        ValueError,
        match="after start",
    ):
        calibrate_v2_interval(
            start=start,
            observed=observed,
            treatment=None,
            config=make_config(),
            cache_dir=tmp_path,
        )


def test_config_rejects_empty_diffusion_axis() -> None:
    with pytest.raises(
        ValueError,
        match="diffusion_values",
    ):
        V2CalibrationConfig(
            diffusion_values=(),
            proliferation_values=(
                0.0,
                0.015,
            ),
        )