from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

import nibabel as nib
import numpy as np
import torch

from tumortwin.models import ReactionDiffusion3D
from tumortwin.optimizers import LMoptimizer
from tumortwin.solvers import TorchDiffEqSolver, TorchDiffEqSolverOptions
from tumortwin.types import NibabelNifti, RadiotherapySpecification

EXPECTED_COMMIT = "bedf90a6d47ba48cf5cdb25901967d84730061d1"


class _PatientLike:
    def __init__(self, image: NibabelNifti) -> None:
        self._image = image

    @property
    def brainmask_image(self) -> NibabelNifti:
        return self._image


def _mapping(value: object, *, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return cast(dict[str, object], value)


def _number(mapping: dict[str, object], key: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{key} must be finite")
    return result


def _number_list(mapping: dict[str, object], key: str) -> list[float]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")

    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValueError(f"{key} must contain numeric values")
        result.append(float(item))
    return result


def _make_mask_image(
    mask: np.ndarray,
    spacing: tuple[float, float, float],
) -> NibabelNifti:
    affine = np.diag([*spacing, 1.0]).astype(float)
    image = nib.Nifti1Image(mask.astype(np.float32), affine=affine)
    image.header.set_xyzt_units("mm")
    return NibabelNifti(image=image)


def _radiotherapy(
    metadata: dict[str, object],
    *,
    initial_time: datetime,
) -> RadiotherapySpecification | None:
    days = _number_list(metadata, "radiotherapy_fraction_days")
    doses = _number_list(metadata, "radiotherapy_fraction_doses_gy")
    if len(days) != len(doses):
        raise ValueError("RT fraction days and doses must have equal length")
    if not days:
        return None

    return RadiotherapySpecification(
        alpha=_number(metadata, "alpha_per_gy"),
        alpha_beta_ratio=_number(metadata, "alpha_beta_ratio_gy"),
        times=[initial_time + timedelta(days=day) for day in days],
        doses=doses,
    )


def _build_model(
    *,
    patient: _PatientLike,
    initial_time: datetime,
    diffusion: float,
    proliferation: float,
    radiotherapy: RadiotherapySpecification | None,
) -> ReactionDiffusion3D:
    return ReactionDiffusion3D(
        k=torch.tensor(proliferation, dtype=torch.float32),
        d=torch.tensor(diffusion, dtype=torch.float32),
        theta=torch.tensor(1.0, dtype=torch.float32),
        patient_data=patient,
        initial_time=initial_time,
        radiotherapy_specification=radiotherapy,
        require_grad=False,
        device=torch.device("cpu"),
    )


def _solve(
    *,
    patient: _PatientLike,
    initial_density: np.ndarray,
    start_day: float,
    end_day: float,
    diffusion: float,
    proliferation: float,
    dt_days: float,
    radiotherapy: RadiotherapySpecification | None,
) -> np.ndarray:
    base_time = datetime(2000, 1, 1)
    model_initial_time = base_time + timedelta(days=start_day)
    model = _build_model(
        patient=patient,
        initial_time=model_initial_time,
        diffusion=diffusion,
        proliferation=proliferation,
        radiotherapy=radiotherapy,
    )
    solver = TorchDiffEqSolver(
        model,
        TorchDiffEqSolverOptions(
            step_size=timedelta(days=dt_days),
            method="rk4",
            device=torch.device("cpu"),
            use_adjoint=False,
        ),
    )
    times = [
        model_initial_time,
        model_initial_time + timedelta(days=end_day - start_day),
    ]
    _, states = solver.solve(
        times,
        torch.from_numpy(initial_density.astype(np.float32)),
    )
    return states[-1].detach().cpu().numpy().astype(np.float32)


def _calibrate(
    *,
    patient: _PatientLike,
    initial_density: np.ndarray,
    observed_density: np.ndarray,
    calibration_duration_days: float,
    dt_days: float,
    radiotherapy: RadiotherapySpecification | None,
    diffusion_bounds: tuple[float, float],
    proliferation_bounds: tuple[float, float],
    iterations: int,
) -> tuple[float, float]:
    initial_guess = torch.tensor(
        [
            min(max(0.025, diffusion_bounds[0]), diffusion_bounds[1]),
            min(max(0.05, proliferation_bounds[0]), proliferation_bounds[1]),
        ],
        dtype=torch.float64,
    )
    bounds = torch.tensor(
        [diffusion_bounds, proliferation_bounds],
        dtype=torch.float64,
    )
    observed = torch.from_numpy(observed_density.astype(np.float32)).reshape(-1)

    def model(parameters: torch.Tensor) -> torch.Tensor:
        prediction = _solve(
            patient=patient,
            initial_density=initial_density,
            start_day=0.0,
            end_day=calibration_duration_days,
            diffusion=float(parameters[0]),
            proliferation=float(parameters[1]),
            dt_days=dt_days,
            radiotherapy=radiotherapy,
        )
        return torch.from_numpy(prediction).reshape(-1).double()

    optimizer = LMoptimizer(
        model=model,
        bounds=bounds,
        initial_guess=initial_guess,
        y_data=observed.double(),
    )
    for _ in range(iterations):
        optimizer.step()

    best = optimizer.best_x.detach().cpu()
    return float(best[0]), float(best[1])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-json", type=Path, required=True)
    parser.add_argument("--request-arrays", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    raw: object = json.loads(args.request_json.read_text(encoding="utf-8"))
    metadata = _mapping(raw, name="request")
    if metadata.get("upstream_commit") != EXPECTED_COMMIT:
        raise ValueError("Request references an unexpected TumorTwin commit")

    with np.load(args.request_arrays, allow_pickle=False) as arrays:
        initial = np.asarray(arrays["initial_density"], dtype=np.float32)
        observed = np.asarray(arrays["observed_density"], dtype=np.float32)
        brain_mask = np.asarray(arrays["brain_mask"], dtype=bool)

    spacing_values = _number_list(metadata, "spacing_mm")
    if len(spacing_values) != 3:
        raise ValueError("spacing_mm must contain exactly three values")
    spacing = cast(
        tuple[float, float, float],
        tuple(spacing_values),
    )
    patient = _PatientLike(_make_mask_image(brain_mask, spacing))
    base_time = datetime(2000, 1, 1)
    radiotherapy = _radiotherapy(metadata, initial_time=base_time)

    mode = metadata.get("mode")
    if mode == "frozen":
        diffusion = _number(metadata, "frozen_diffusion")
        proliferation = _number(metadata, "frozen_proliferation")
    elif mode == "calibrate":
        diffusion_bounds_values = _number_list(metadata, "diffusion_bounds")
        proliferation_bounds_values = _number_list(
            metadata,
            "proliferation_bounds",
        )
        if len(diffusion_bounds_values) != 2:
            raise ValueError("diffusion_bounds must contain two values")
        if len(proliferation_bounds_values) != 2:
            raise ValueError("proliferation_bounds must contain two values")
        iterations_raw = metadata.get("optimizer_iterations")
        if type(iterations_raw) is not int:
            raise ValueError("optimizer_iterations must be integer")

        diffusion, proliferation = _calibrate(
            patient=patient,
            initial_density=initial,
            observed_density=observed,
            calibration_duration_days=_number(
                metadata,
                "calibration_duration_days",
            ),
            dt_days=_number(metadata, "dt_days"),
            radiotherapy=radiotherapy,
            diffusion_bounds=(
                diffusion_bounds_values[0],
                diffusion_bounds_values[1],
            ),
            proliferation_bounds=(
                proliferation_bounds_values[0],
                proliferation_bounds_values[1],
            ),
            iterations=cast(int, iterations_raw),
        )
    else:
        raise ValueError(f"Unsupported reference mode: {mode!r}")

    calibration_duration = _number(
        metadata,
        "calibration_duration_days",
    )
    forecast_duration = _number(
        metadata,
        "forecast_duration_days",
    )
    prediction = _solve(
        patient=patient,
        initial_density=observed,
        start_day=calibration_duration,
        end_day=calibration_duration + forecast_duration,
        diffusion=diffusion,
        proliferation=proliferation,
        dt_days=_number(metadata, "dt_days"),
        radiotherapy=radiotherapy,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output_dir / "result_arrays.npz",
        prediction_density=prediction,
    )
    result = {
        "schema_version": 1,
        "upstream_commit": EXPECTED_COMMIT,
        "mode": mode,
        "diffusion": diffusion,
        "proliferation": proliferation,
    }
    (args.output_dir / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
