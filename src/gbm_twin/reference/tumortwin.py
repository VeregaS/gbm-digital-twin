from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import numpy as np


TUMORTWIN_REPOSITORY = "https://github.com/OncologyModelingGroup/TumorTwin.git"
TUMORTWIN_COMMIT = "bedf90a6d47ba48cf5cdb25901967d84730061d1"


@dataclass(frozen=True)
class TumorTwinReferenceRequest:
    patient_id: int
    initial_density: np.ndarray
    observed_density: np.ndarray
    brain_mask: np.ndarray
    spacing_mm: tuple[float, float, float]
    calibration_duration_days: float
    forecast_duration_days: float
    dt_days: float
    radiotherapy_fraction_days: tuple[float, ...]
    radiotherapy_fraction_doses_gy: tuple[float, ...]
    alpha_per_gy: float
    alpha_beta_ratio_gy: float
    mode: Literal["frozen", "calibrate"]
    frozen_diffusion: float | None = None
    frozen_proliferation: float | None = None
    diffusion_bounds: tuple[float, float] = (0.0, 0.06)
    proliferation_bounds: tuple[float, float] = (0.0, 0.11)
    optimizer_iterations: int = 8

    def __post_init__(self) -> None:
        shape = self.initial_density.shape
        if len(shape) != 3:
            raise ValueError("initial_density must be 3D")
        if self.observed_density.shape != shape:
            raise ValueError("observed_density must match initial_density")
        if self.brain_mask.shape != shape:
            raise ValueError("brain_mask must match initial_density")
        for array, name in (
            (self.initial_density, "initial_density"),
            (self.observed_density, "observed_density"),
        ):
            if not np.all(np.isfinite(array)):
                raise ValueError(f"{name} must contain finite values")
            if np.any(array < 0.0) or np.any(array > 1.0):
                raise ValueError(f"{name} must be within [0, 1]")

        if any(value <= 0.0 or not math.isfinite(value) for value in self.spacing_mm):
            raise ValueError("spacing_mm must be finite and positive")
        if self.calibration_duration_days <= 0.0:
            raise ValueError("calibration_duration_days must be positive")
        if self.forecast_duration_days <= 0.0:
            raise ValueError("forecast_duration_days must be positive")
        if self.dt_days <= 0.0:
            raise ValueError("dt_days must be positive")
        if len(self.radiotherapy_fraction_days) != len(
            self.radiotherapy_fraction_doses_gy
        ):
            raise ValueError("RT fraction days and doses must have equal length")
        if any(day < 0.0 for day in self.radiotherapy_fraction_days):
            raise ValueError("RT fraction days must be non-negative")
        if any(dose <= 0.0 for dose in self.radiotherapy_fraction_doses_gy):
            raise ValueError("RT fraction doses must be positive")
        if self.alpha_per_gy <= 0.0 or self.alpha_beta_ratio_gy <= 0.0:
            raise ValueError("radiobiology parameters must be positive")
        if self.mode == "frozen":
            if self.frozen_diffusion is None or self.frozen_proliferation is None:
                raise ValueError("frozen mode requires D and rho")
        for bounds, name in (
            (self.diffusion_bounds, "diffusion_bounds"),
            (self.proliferation_bounds, "proliferation_bounds"),
        ):
            if bounds[0] < 0.0 or bounds[1] <= bounds[0]:
                raise ValueError(f"{name} must be ordered and non-negative")
        if self.optimizer_iterations < 1:
            raise ValueError("optimizer_iterations must be positive")


@dataclass(frozen=True)
class TumorTwinReferenceResult:
    prediction_density: np.ndarray
    diffusion: float
    proliferation: float
    upstream_commit: str
    mode: str


def write_reference_request(
    request: TumorTwinReferenceRequest,
    directory: Path,
) -> tuple[Path, Path]:
    root = directory.resolve()
    root.mkdir(parents=True, exist_ok=True)

    arrays_path = root / "request_arrays.npz"
    np.savez_compressed(
        arrays_path,
        initial_density=np.asarray(request.initial_density, dtype=np.float32),
        observed_density=np.asarray(request.observed_density, dtype=np.float32),
        brain_mask=np.asarray(request.brain_mask, dtype=np.uint8),
    )
    metadata = {
        "schema_version": 1,
        "patient_id": request.patient_id,
        "spacing_mm": list(request.spacing_mm),
        "calibration_duration_days": request.calibration_duration_days,
        "forecast_duration_days": request.forecast_duration_days,
        "dt_days": request.dt_days,
        "radiotherapy_fraction_days": list(request.radiotherapy_fraction_days),
        "radiotherapy_fraction_doses_gy": list(
            request.radiotherapy_fraction_doses_gy
        ),
        "alpha_per_gy": request.alpha_per_gy,
        "alpha_beta_ratio_gy": request.alpha_beta_ratio_gy,
        "mode": request.mode,
        "frozen_diffusion": request.frozen_diffusion,
        "frozen_proliferation": request.frozen_proliferation,
        "diffusion_bounds": list(request.diffusion_bounds),
        "proliferation_bounds": list(request.proliferation_bounds),
        "optimizer_iterations": request.optimizer_iterations,
        "upstream_repository": TUMORTWIN_REPOSITORY,
        "upstream_commit": TUMORTWIN_COMMIT,
    }
    metadata_path = root / "request.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return metadata_path, arrays_path


def load_reference_result(directory: Path) -> TumorTwinReferenceResult:
    root = directory.resolve()
    metadata_path = root / "result.json"
    arrays_path = root / "result_arrays.npz"
    if not metadata_path.is_file() or not arrays_path.is_file():
        raise FileNotFoundError("TumorTwin reference result is incomplete")

    raw: object = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("TumorTwin result metadata must be a JSON object")
    metadata = cast(dict[str, object], raw)

    with np.load(arrays_path, allow_pickle=False) as arrays:
        prediction = np.asarray(arrays["prediction_density"], dtype=np.float32)

    commit = metadata.get("upstream_commit")
    mode = metadata.get("mode")
    diffusion = metadata.get("diffusion")
    proliferation = metadata.get("proliferation")
    if commit != TUMORTWIN_COMMIT:
        raise ValueError("TumorTwin result came from an unexpected upstream commit")
    if not isinstance(mode, str):
        raise ValueError("TumorTwin result mode is invalid")
    if isinstance(diffusion, bool) or not isinstance(diffusion, (int, float)):
        raise ValueError("TumorTwin result diffusion is invalid")
    if isinstance(proliferation, bool) or not isinstance(
        proliferation, (int, float)
    ):
        raise ValueError("TumorTwin result proliferation is invalid")

    return TumorTwinReferenceResult(
        prediction_density=prediction,
        diffusion=float(diffusion),
        proliferation=float(proliferation),
        upstream_commit=commit,
        mode=mode,
    )


def run_external_tumortwin(
    *,
    python_executable: Path,
    worker_script: Path,
    request: TumorTwinReferenceRequest,
    work_dir: Path,
    timeout_seconds: int = 3600,
) -> TumorTwinReferenceResult:
    if not python_executable.is_file():
        raise FileNotFoundError(
            f"TumorTwin Python executable not found: {python_executable}"
        )
    if not worker_script.is_file():
        raise FileNotFoundError(
            f"TumorTwin worker script not found: {worker_script}"
        )

    request_dir = work_dir.resolve()
    metadata_path, arrays_path = write_reference_request(request, request_dir)
    command = [
        str(python_executable),
        str(worker_script.resolve()),
        "--request-json",
        str(metadata_path),
        "--request-arrays",
        str(arrays_path),
        "--output-dir",
        str(request_dir),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        raise RuntimeError(
            "TumorTwin worker failed with exit code "
            f"{completed.returncode}. stdout={stdout!r}; stderr={stderr!r}"
        )

    return load_reference_result(request_dir)
