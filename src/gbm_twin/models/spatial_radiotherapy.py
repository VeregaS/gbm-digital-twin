from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

DoseUnit = Literal["gy", "cgy"]


@dataclass(frozen=True)
class DoseNormalizationResult:
    dose_gy: np.ndarray
    source_unit: DoseUnit
    scale_to_gy: float
    max_dose_gy: float


def _as_nonnegative_finite_field(
    value: np.ndarray,
    *,
    name: str,
) -> np.ndarray:
    field = np.asarray(value, dtype=np.float64)

    if field.ndim != 3:
        raise ValueError(f"{name} must be 3D")

    if not np.all(np.isfinite(field)):
        raise ValueError(f"{name} must contain finite values")

    if np.any(field < 0.0):
        raise ValueError(f"{name} must be non-negative")

    return field


def normalize_cumulative_rtdose_to_gy(
    raw_dose: np.ndarray,
    *,
    prescribed_total_dose_gy: float,
    unit: Literal["auto", "gy", "cgy"] = "auto",
    plausible_ratio_range: tuple[float, float] = (0.5, 1.5),
) -> DoseNormalizationResult:
    """Normalize RTDOSE values to Gy with a guarded unit check.

    In ``auto`` mode only two interpretations are accepted: Gy directly or
    cGy divided by 100. The maximum dose must then be plausibly close to the
    prescribed course dose. Ambiguous/unexpected maps fail closed rather than
    silently introducing a 100x radiobiology error.
    """

    dose = _as_nonnegative_finite_field(raw_dose, name="raw_dose")

    if prescribed_total_dose_gy <= 0.0:
        raise ValueError("prescribed_total_dose_gy must be positive")

    lower_ratio, upper_ratio = plausible_ratio_range

    if not 0.0 < lower_ratio < upper_ratio:
        raise ValueError("plausible_ratio_range must be positive and ordered")

    raw_max = float(np.max(dose))

    if raw_max <= 0.0:
        raise ValueError("RTDOSE map contains no positive dose")

    def plausible(max_gy: float) -> bool:
        ratio = max_gy / prescribed_total_dose_gy
        return lower_ratio <= ratio <= upper_ratio

    if unit == "gy":
        scale = 1.0
        source_unit: DoseUnit = "gy"
    elif unit == "cgy":
        scale = 0.01
        source_unit = "cgy"
    elif unit == "auto":
        gy_plausible = plausible(raw_max)
        cgy_plausible = plausible(raw_max * 0.01)

        if gy_plausible == cgy_plausible:
            raise ValueError(
                "Unable to infer RTDOSE unit safely from prescription; "
                "specify unit='gy' or unit='cgy' after verifying metadata"
            )

        if gy_plausible:
            scale = 1.0
            source_unit = "gy"
        else:
            scale = 0.01
            source_unit = "cgy"
    else:
        raise ValueError("unit must be 'auto', 'gy', or 'cgy'")

    normalized = np.asarray(dose * scale, dtype=np.float32)
    max_gy = float(np.max(normalized))

    if not plausible(max_gy):
        raise ValueError(
            "Normalized RTDOSE maximum is inconsistent with prescribed dose"
        )

    return DoseNormalizationResult(
        dose_gy=normalized,
        source_unit=source_unit,
        scale_to_gy=scale,
        max_dose_gy=max_gy,
    )


def per_fraction_dose_from_cumulative_plan(
    cumulative_dose_gy: np.ndarray,
    *,
    prescribed_total_dose_gy: float,
    dose_per_fraction_gy: float,
) -> np.ndarray:
    """Scale a cumulative RTDOSE map to one fraction.

    This operator is valid only under the explicit assumption that every
    modeled fraction shares the same *relative* spatial dose distribution.
    The assumption is reasonable for a single plan with uniform fractionation
    but must not be silently used for sequential boost/adaptive plans.
    """

    total = _as_nonnegative_finite_field(
        cumulative_dose_gy,
        name="cumulative_dose_gy",
    )

    if prescribed_total_dose_gy <= 0.0:
        raise ValueError("prescribed_total_dose_gy must be positive")

    if dose_per_fraction_gy <= 0.0:
        raise ValueError("dose_per_fraction_gy must be positive")

    if dose_per_fraction_gy > prescribed_total_dose_gy:
        raise ValueError(
            "dose_per_fraction_gy cannot exceed prescribed total dose"
        )

    scale = dose_per_fraction_gy / prescribed_total_dose_gy
    return np.asarray(total * scale, dtype=np.float32)


def lq_survival_field(
    dose_gy: np.ndarray,
    *,
    alpha_per_gy: float,
    beta_per_gy2: float,
) -> np.ndarray:
    dose = _as_nonnegative_finite_field(dose_gy, name="dose_gy")

    if alpha_per_gy < 0.0:
        raise ValueError("alpha_per_gy must be non-negative")

    if beta_per_gy2 < 0.0:
        raise ValueError("beta_per_gy2 must be non-negative")

    exponent = -(
        alpha_per_gy * dose
        + beta_per_gy2 * dose**2
    )

    survival = np.exp(exponent)
    np.clip(survival, 0.0, 1.0, out=survival)

    return survival.astype(np.float32, copy=False)


def apply_spatial_pirt_fraction(
    field: np.ndarray,
    *,
    survival_fraction: np.ndarray,
    domain_mask: np.ndarray | None = None,
) -> np.ndarray:
    concentration = np.asarray(field)
    survival = np.asarray(survival_fraction)

    if concentration.ndim != 3:
        raise ValueError("field must be 3D")

    if survival.shape != concentration.shape:
        raise ValueError("survival_fraction must match field shape")

    if not np.all(np.isfinite(concentration)):
        raise ValueError("field must contain finite values")

    if np.any(concentration < 0.0) or np.any(concentration > 1.0):
        raise ValueError("field must be within [0, 1]")

    if not np.all(np.isfinite(survival)):
        raise ValueError("survival_fraction must contain finite values")

    if np.any(survival < 0.0) or np.any(survival > 1.0):
        raise ValueError("survival_fraction must be within [0, 1]")

    dtype = np.float32 if concentration.dtype == np.float32 else np.float64
    source = concentration.astype(dtype, copy=False)
    sf = survival.astype(dtype, copy=False)

    loss = (1.0 - sf) * source * (1.0 - source)

    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)

        if domain.shape != source.shape:
            raise ValueError("domain_mask must match field shape")

        loss = np.where(domain, loss, 0.0)

    result = source - loss
    np.clip(result, 0.0, 1.0, out=result)

    return result.astype(dtype, copy=False)
