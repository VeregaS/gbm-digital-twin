from __future__ import annotations

import numpy as np


def pirt_radiation_loss(
    field: np.ndarray,
    *,
    survival_fraction: float,
    domain_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Compute the Rockne/PIRT radiation loss for one treatment fraction.

    The tumor state is assumed to be normalized by carrying capacity:

        0 <= c <= 1

    Therefore K = 1 and the radiation loss is

        R = (1 - S) * c * (1 - c)

    where S is the LQ surviving fraction.
    """

    source = np.asarray(field)

    if source.ndim != 3:
        raise ValueError(
            "field must be 3-dimensional"
        )

    if not np.all(
        np.isfinite(source)
    ):
        raise ValueError(
            "field must contain only finite values"
        )

    if np.any(
        source < 0.0
    ) or np.any(
        source > 1.0
    ):
        raise ValueError(
            "field values must be within [0, 1]"
        )

    if not np.isfinite(
        survival_fraction
    ):
        raise ValueError(
            "survival_fraction must be finite"
        )

    if not (
        0.0
        <= survival_fraction
        <= 1.0
    ):
        raise ValueError(
            "survival_fraction must be within [0, 1]"
        )

    dtype = (
        np.float32
        if source.dtype == np.float32
        else np.float64
    )

    concentration = source.astype(
        dtype,
        copy=False,
    )

    loss = (
        (1.0 - survival_fraction)
        * concentration
        * (1.0 - concentration)
    )

    if domain_mask is not None:
        domain = np.asarray(
            domain_mask,
            dtype=bool,
        )

        if domain.shape != source.shape:
            raise ValueError(
                "domain_mask must have the same "
                "shape as field"
            )

        loss = np.where(
            domain,
            loss,
            0.0,
        )

    return loss.astype(
        dtype,
        copy=False,
    )


def apply_pirt_fraction(
    field: np.ndarray,
    *,
    survival_fraction: float,
    domain_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Apply one PIRT-style treatment-fraction update.

    For normalized carrying capacity K = 1:

        c_new = c - (1 - S) * c * (1 - c)
    """

    source = np.asarray(field)

    loss = pirt_radiation_loss(
        source,
        survival_fraction=survival_fraction,
        domain_mask=domain_mask,
    )

    result = source.astype(
        loss.dtype,
        copy=True,
    )

    result -= loss

    np.clip(
        result,
        0.0,
        1.0,
        out=result,
    )

    return result