from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gbm_twin.reference.tumortwin import (
    TUMORTWIN_COMMIT,
    TumorTwinReferenceRequest,
    load_reference_result,
    write_reference_request,
)


def _request() -> TumorTwinReferenceRequest:
    shape = (5, 5, 5)
    initial = np.zeros(shape, dtype=np.float32)
    initial[2, 2, 2] = 0.8
    observed = initial.copy()
    mask = np.ones(shape, dtype=bool)

    return TumorTwinReferenceRequest(
        patient_id=8,
        initial_density=initial,
        observed_density=observed,
        brain_mask=mask,
        spacing_mm=(2.0, 2.0, 2.0),
        calibration_duration_days=30.0,
        forecast_duration_days=40.0,
        dt_days=2.0,
        radiotherapy_fraction_days=(1.0, 2.0),
        radiotherapy_fraction_doses_gy=(2.0, 2.0),
        alpha_per_gy=0.01,
        alpha_beta_ratio_gy=10.0,
        mode="frozen",
        frozen_diffusion=0.01,
        frozen_proliferation=0.02,
    )


def test_reference_request_round_trip_files(tmp_path: Path) -> None:
    metadata_path, arrays_path = write_reference_request(
        _request(),
        tmp_path,
    )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["upstream_commit"] == TUMORTWIN_COMMIT
    assert metadata["mode"] == "frozen"

    with np.load(arrays_path, allow_pickle=False) as arrays:
        assert arrays["initial_density"].shape == (5, 5, 5)
        assert arrays["brain_mask"].dtype == np.uint8


def test_reference_request_rejects_missing_frozen_parameters() -> None:
    request = _request()

    with pytest.raises(ValueError, match="requires D and rho"):
        TumorTwinReferenceRequest(
            **{
                **request.__dict__,
                "frozen_diffusion": None,
            }
        )


def test_reference_result_requires_pinned_commit(tmp_path: Path) -> None:
    np.savez_compressed(
        tmp_path / "result_arrays.npz",
        prediction_density=np.zeros((3, 3, 3), dtype=np.float32),
    )
    (tmp_path / "result.json").write_text(
        json.dumps(
            {
                "upstream_commit": "wrong",
                "mode": "frozen",
                "diffusion": 0.01,
                "proliferation": 0.02,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unexpected upstream commit"):
        load_reference_result(tmp_path)
