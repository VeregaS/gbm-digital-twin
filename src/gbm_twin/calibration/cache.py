import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    PIRTFractionatedRadiotherapy,
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
    TreatmentWindow,
)

CALIBRATION_CACHE_VERSION = 1


def array_digest(
    array: np.ndarray,
) -> str:
    contiguous = np.ascontiguousarray(
        array
    )

    digest = hashlib.sha256()

    digest.update(
        str(contiguous.dtype).encode(
            "utf-8"
        )
    )

    digest.update(
        np.asarray(
            contiguous.shape,
            dtype=np.int64,
        ).tobytes()
    )

    digest.update(
        contiguous.data
    )

    return digest.hexdigest()


def treatment_signature(
    treatment: object | None,
) -> dict[str, Any] | None:
    if treatment is None:
        return None

    if isinstance(
        treatment,
        TreatmentWindow,
    ):
        return {
            "type": "treatment_window",
            "start_day": float(
                treatment.start_day
            ),
            "end_day": float(
                treatment.end_day
            ),
            "kill_rate": float(
                treatment.kill_rate
            ),
        }

    if isinstance(
        treatment,
        PostRadiotherapyEffect,
    ):
        return {
            "type": "post_rt_effect",
            "start_day": float(
                treatment.start_day
            ),
            "initial_kill_rate": float(
                treatment.initial_kill_rate
            ),
            "decay_time_days": float(
                treatment.decay_time_days
            ),
        }
        
    if isinstance(
        treatment,
        PIRTFractionatedRadiotherapy,
    ):
        return {
            "type": "pirt_fractionated_rt",
            "fraction_days": [
                float(day)
                for day
                in treatment.fraction_days
            ],
            "dose_per_fraction_gy": float(
                treatment
                .dose_per_fraction_gy
            ),
            "alpha_per_gy": float(
                treatment.alpha_per_gy
            ),
            "beta_per_gy2": float(
                treatment.beta_per_gy2
            ),
        }

    if isinstance(
        treatment,
        FractionatedRadiotherapy,
    ):
        return {
            "type": "fractionated_rt",
            "fraction_days": [
                float(day)
                for day
                in treatment.fraction_days
            ],
            "dose_per_fraction_gy": float(
                treatment
                .dose_per_fraction_gy
            ),
            "alpha_per_gy": float(
                treatment.alpha_per_gy
            ),
            "beta_per_gy2": float(
                treatment.beta_per_gy2
            ),
        }

    if isinstance(
        treatment,
        RadiotherapyProtocol,
    ):
        return {
            "type": "rt_protocol",
            "fractions": (
                treatment_signature(
                    treatment.fractions
                )
            ),
            "post_effect": (
                treatment_signature(
                    treatment.post_effect
                )
            ),
        }

    raise TypeError(
        f"Unsupported treatment type: "
        f"{type(treatment).__name__}"
    )


def build_calibration_signature(
    *,
    initial_field: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    threshold: float,
    treatment: object | None,
    start_time_day: float,
) -> dict[str, Any]:
    return {
        "cache_version": (
            CALIBRATION_CACHE_VERSION
        ),
        "solver_dtype": str(
            initial_field.dtype
        ),
        "initial_digest": array_digest(
            initial_field
        ),
        "observed_digest": array_digest(
            observed_mask
        ),
        "domain_digest": array_digest(
            domain_mask
        ),
        "spacing": [
            float(value)
            for value in spacing
        ],
        "duration_days": float(
            duration_days
        ),
        "dt": float(dt),
        "threshold": float(
            threshold
        ),
        "start_time_day": float(
            start_time_day
        ),
        "treatment": (
            treatment_signature(
                treatment
            )
        ),
    }


def candidate_cache_key(
    signature: dict[str, Any],
    *,
    diffusion: float,
    proliferation: float,
) -> str:
    payload = {
        "signature": signature,
        "diffusion": float(
            diffusion
        ),
        "proliferation": float(
            proliferation
        ),
    }

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(
        encoded
    ).hexdigest()


def load_cached_metrics(
    cache_dir: Path,
    key: str,
) -> tuple[float, float] | None:
    path = (
        cache_dir
        / key[:2]
        / f"{key}.json"
    )

    if not path.exists():
        return None

    try:
        payload = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    if (
        payload.get("cache_version")
        != CALIBRATION_CACHE_VERSION
    ):
        return None

    try:
        dice = float(
            payload["dice"]
        )

        volume_error = float(
            payload["volume_error"]
        )
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None

    return (
        dice,
        volume_error,
    )


def save_cached_metrics(
    cache_dir: Path,
    key: str,
    *,
    dice: float,
    volume_error: float,
) -> None:
    directory = (
        cache_dir
        / key[:2]
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        directory
        / f"{key}.json"
    )

    payload = {
        "cache_version": (
            CALIBRATION_CACHE_VERSION
        ),
        "dice": float(dice),
        "volume_error": float(
            volume_error
        ),
    }

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=f"{key}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            json.dump(
                payload,
                file,
                sort_keys=True,
            )

            temporary_path = Path(
                file.name
            )

        os.replace(
            temporary_path,
            destination,
        )

    finally:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()