from __future__ import annotations

import numpy as np

TUMORTWIN_NONENHANCING_CELLULARITY = 0.16


def adc_water_reference(adc: np.ndarray) -> float:
    """Mirror TumorTwin's ADC unit heuristic at the pinned reference commit."""

    values = np.asarray(adc, dtype=float)
    if values.size == 0:
        raise ValueError("ADC array must not be empty")
    if not np.all(np.isfinite(values)):
        raise ValueError("ADC array must contain only finite values")

    log10_array = np.log10(np.maximum(values, 1e-10))
    max_log10 = float(np.max(log10_array))

    if max_log10 > 3:
        return 3000.0
    if 2 < max_log10 <= 3:
        return 300.0
    if 1 < max_log10 <= 2:
        return 30.0
    if 0 < max_log10 <= 1:
        return 3.0
    if -1 < max_log10 <= 0:
        return 0.3
    if -2 < max_log10 <= -1:
        return 0.03
    if -3 < max_log10 <= -2:
        return 0.003
    return 3.0


def tumortwin_adc_to_cellularity(
    adc: np.ndarray,
    enhancing_mask: np.ndarray,
    nonenhancing_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Reproduce the pinned TumorTwin ADC-to-cellularity preprocessing.

    The implementation intentionally mirrors the upstream
    ADC_to_cellularity function from the pinned reference commit. It is kept
    in the main project environment so the expensive reference solver can
    receive precomputed cellularity fields without importing TumorTwin's
    incompatible numerical dependency pins.

    For the first CFB fidelity benchmark only the enhancing GTV mask is used.
    A non-enhancing mask must be supplied explicitly; raw FLAIR intensity is
    never thresholded implicitly.
    """

    adc_array = np.asarray(adc, dtype=float)
    enhancing = np.asarray(enhancing_mask, dtype=bool)

    if adc_array.ndim != 3:
        raise ValueError("ADC array must be 3D")
    if enhancing.shape != adc_array.shape:
        raise ValueError("enhancing mask must match ADC shape")

    nonenhancing: np.ndarray | None = None
    if nonenhancing_mask is not None:
        nonenhancing = np.asarray(nonenhancing_mask, dtype=bool)
        if nonenhancing.shape != adc_array.shape:
            raise ValueError("nonenhancing mask must match ADC shape")

    adc_w = adc_water_reference(adc_array)
    total = np.abs((adc_w - adc_array) / adc_w)
    result = np.zeros(adc_array.shape, dtype=np.float32)

    if nonenhancing is not None:
        result[nonenhancing] = TUMORTWIN_NONENHANCING_CELLULARITY

    result[enhancing] = total[enhancing]
    return np.clip(result, 0.0, 1.0).astype(np.float32, copy=False)
