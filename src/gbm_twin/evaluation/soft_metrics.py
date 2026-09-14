import numpy as np


def soft_threshold_membership(
    field: np.ndarray,
    *,
    threshold: float,
    temperature: float,
    domain_mask: np.ndarray | None = None,
) -> np.ndarray:
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            "threshold must be within [0, 1]"
        )

    if temperature <= 0:
        raise ValueError(
            "temperature must be positive"
        )

    values = np.asarray(
        field,
        dtype=np.float64,
    )

    scaled = (
        values - threshold
    ) / temperature

    scaled = np.clip(
        scaled,
        -60.0,
        60.0,
    )

    membership = (
        1.0
        / (
            1.0
            + np.exp(-scaled)
        )
    )

    if domain_mask is not None:
        domain = np.asarray(
            domain_mask,
            dtype=bool,
        )

        if domain.shape != values.shape:
            raise ValueError(
                "domain_mask must have "
                "the same shape as field"
            )

        membership = np.where(
            domain,
            membership,
            0.0,
        )

    return membership


def soft_dice_score(
    predicted_membership: np.ndarray,
    observed_mask: np.ndarray,
) -> float:
    predicted = np.asarray(
        predicted_membership,
        dtype=np.float64,
    )

    observed = np.asarray(
        observed_mask,
        dtype=bool,
    )

    if predicted.shape != observed.shape:
        raise ValueError(
            "Predicted membership and observed "
            "mask must have the same shape"
        )

    if not np.all(
        np.isfinite(predicted)
    ):
        raise ValueError(
            "Predicted membership must be finite"
        )

    if np.any(
        (predicted < 0.0)
        | (predicted > 1.0)
    ):
        raise ValueError(
            "Predicted membership must be "
            "within [0, 1]"
        )

    observed_float = observed.astype(
        np.float64,
        copy=False,
    )

    intersection = float(
        np.sum(
            predicted
            * observed_float,
            dtype=np.float64,
        )
    )

    predicted_sum = float(
        np.sum(
            predicted,
            dtype=np.float64,
        )
    )

    observed_sum = float(
        np.sum(
            observed_float,
            dtype=np.float64,
        )
    )

    denominator = (
        predicted_sum
        + observed_sum
    )

    if denominator == 0.0:
        return 1.0

    return (
        2.0
        * intersection
        / denominator
    )


def soft_relative_volume_error(
    predicted_membership: np.ndarray,
    observed_mask: np.ndarray,
) -> float:
    predicted = np.asarray(
        predicted_membership,
        dtype=np.float64,
    )

    observed = np.asarray(
        observed_mask,
        dtype=bool,
    )

    if predicted.shape != observed.shape:
        raise ValueError(
            "Predicted membership and observed "
            "mask must have the same shape"
        )

    if not np.all(
        np.isfinite(predicted)
    ):
        raise ValueError(
            "Predicted membership must be finite"
        )

    if np.any(
        (predicted < 0.0)
        | (predicted > 1.0)
    ):
        raise ValueError(
            "Predicted membership must be "
            "within [0, 1]"
        )

    predicted_volume = float(
        np.sum(
            predicted,
            dtype=np.float64,
        )
    )

    observed_volume = float(
        np.count_nonzero(
            observed
        )
    )

    if observed_volume == 0.0:
        if predicted_volume == 0.0:
            return 0.0

        return float("inf")

    return (
        abs(
            predicted_volume
            - observed_volume
        )
        / observed_volume
    )