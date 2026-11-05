from __future__ import annotations

import argparse
import math
import shutil
import tempfile
from pathlib import Path

import numpy as np

from gbm_twin.reference.tumortwin import (
    TumorTwinReferenceRequest,
    run_external_tumortwin,
)


def _logistic(c0: float, rate: float, days: float) -> float:
    numerator = c0 * math.exp(rate * days)
    denominator = 1.0 - c0 + numerator
    return numerator / denominator


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Smoke-test the isolated pinned TumorTwin environment on a "
            "synthetic no-diffusion logistic-growth case."
        )
    )
    parser.add_argument(
        "--tumortwin-python",
        type=Path,
        default=Path(".reference/tumortwin-venv/Scripts/python.exe"),
    )
    parser.add_argument(
        "--worker-script",
        type=Path,
        default=Path("scripts/reference/tumortwin_worker.py"),
    )
    args = parser.parse_args()

    shape = (7, 7, 7)
    initial = np.zeros(shape, dtype=np.float32)
    mask = np.ones(shape, dtype=bool)
    initial[3, 3, 3] = 0.2
    observed = initial.copy()

    request = TumorTwinReferenceRequest(
        patient_id=0,
        initial_density=initial,
        observed_density=observed,
        brain_mask=mask,
        spacing_mm=(2.0, 2.0, 2.0),
        calibration_duration_days=1.0,
        forecast_duration_days=10.0,
        dt_days=0.5,
        radiotherapy_fraction_days=(),
        radiotherapy_fraction_doses_gy=(),
        alpha_per_gy=0.01,
        alpha_beta_ratio_gy=10.0,
        mode="frozen",
        frozen_diffusion=0.0,
        frozen_proliferation=0.03,
    )

    temporary = Path(tempfile.mkdtemp(prefix="gbm-tumortwin-smoke-"))
    try:
        result = run_external_tumortwin(
            python_executable=args.tumortwin_python.resolve(),
            worker_script=args.worker_script.resolve(),
            request=request,
            work_dir=temporary,
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

    actual = float(result.prediction_density[3, 3, 3])
    expected = _logistic(0.2, 0.03, 10.0)
    error = abs(actual - expected)

    print(f"TumorTwin synthetic value: {actual:.8f}")
    print(f"Analytic logistic value: {expected:.8f}")
    print(f"Absolute error: {error:.8g}")
    if error > 5e-4:
        raise SystemExit(
            "TumorTwin smoke test failed: error exceeds 5e-4"
        )

    print("TumorTwin smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
