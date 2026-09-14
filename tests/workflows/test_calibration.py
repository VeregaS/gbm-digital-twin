from pathlib import Path

import numpy as np
import pytest

import gbm_twin.workflows.calibration as calibration_module
from gbm_twin.calibration.grid_search import (
    CalibrationResult,
)
from gbm_twin.data.nifti import NiftiVolume
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    calibrate_v2_interval,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)


def make_volume(
    name: str,
) -> NiftiVolume:
    data = np.zeros(
        (5, 5, 5),
        dtype=np.float32,
    )

    data[
        2,
        2,
        2,
    ] = 1.0

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
        ),
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

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        calibration_module,
        "latent_state_from_gtv",
        lambda *args, **kwargs: (
            np.zeros(
                (5, 5, 5),
                dtype=np.float32,
            )
        ),
    )

    expected = CalibrationResult(
        diffusion=0.03,
        proliferation=0.015,
        dice=0.8,
        volume_error=0.1,
        loss=0.25,
    )

    def fake_grid_search(
        initial,
        observed_mask,
        domain,
        **kwargs,
    ):
        captured.update(kwargs)

        assert initial.shape == (
            5,
            5,
            5,
        )

        assert observed_mask.shape == (
            5,
            5,
            5,
        )

        assert domain.shape == (
            5,
            5,
            5,
        )

        return [expected]

    monkeypatch.setattr(
        calibration_module,
        "grid_search",
        fake_grid_search,
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

    assert (
        result.start_timepoint
        == "t0"
    )

    assert (
        result.observed_timepoint
        == "t1"
    )

    assert result.duration_days == 77.0
    assert result.best == expected

    assert (
        captured["duration_days"]
        == 77.0
    )

    assert (
        captured["start_time_day"]
        == 0.0
    )

    assert (
        captured["objective"]
        == "soft"
    )

    assert (
        captured["soft_temperature"]
        == 0.05
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


def test_config_rejects_empty_diffusion_axis(
) -> None:
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