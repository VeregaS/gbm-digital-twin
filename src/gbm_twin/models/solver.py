import math

import numpy as np

from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    TreatmentWindow,
)

_TOLERANCE = 1e-9


def laplacian_3d(
    field: np.ndarray,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    if field.ndim != 3:
        raise ValueError(
            f"Expected 3D field, got shape {field.shape}"
        )

    if any(value <= 0 for value in spacing):
        raise ValueError(
            "Spacing values must be positive"
        )

    dx, dy, dz = spacing

    padded = np.pad(
        field,
        pad_width=1,
        mode="edge",
    )

    center = padded[
        1:-1,
        1:-1,
        1:-1,
    ]

    d2x = (
        padded[
            2:,
            1:-1,
            1:-1,
        ]
        - 2.0 * center
        + padded[
            :-2,
            1:-1,
            1:-1,
        ]
    ) / dx**2

    d2y = (
        padded[
            1:-1,
            2:,
            1:-1,
        ]
        - 2.0 * center
        + padded[
            1:-1,
            :-2,
            1:-1,
        ]
    ) / dy**2

    d2z = (
        padded[
            1:-1,
            1:-1,
            2:,
        ]
        - 2.0 * center
        + padded[
            1:-1,
            1:-1,
            :-2,
        ]
    ) / dz**2

    return d2x + d2y + d2z


def masked_laplacian_3d(
    field: np.ndarray,
    mask: np.ndarray,
    spacing: tuple[float, float, float],
) -> np.ndarray:
    if field.ndim != 3:
        raise ValueError(
            f"Expected 3D field, got shape {field.shape}"
        )

    if mask.shape != field.shape:
        raise ValueError(
            f"Mask shape {mask.shape} "
            f"does not match field shape {field.shape}"
        )

    if any(value <= 0 for value in spacing):
        raise ValueError(
            "Spacing values must be positive"
        )

    mask = mask.astype(bool)

    dx, dy, dz = spacing

    padded_field = np.pad(
        field,
        pad_width=1,
        mode="constant",
        constant_values=0,
    )

    padded_mask = np.pad(
        mask,
        pad_width=1,
        mode="constant",
        constant_values=False,
    )

    center = padded_field[
        1:-1,
        1:-1,
        1:-1,
    ]

    x_plus = np.where(
        padded_mask[
            2:,
            1:-1,
            1:-1,
        ],
        padded_field[
            2:,
            1:-1,
            1:-1,
        ],
        center,
    )

    x_minus = np.where(
        padded_mask[
            :-2,
            1:-1,
            1:-1,
        ],
        padded_field[
            :-2,
            1:-1,
            1:-1,
        ],
        center,
    )

    y_plus = np.where(
        padded_mask[
            1:-1,
            2:,
            1:-1,
        ],
        padded_field[
            1:-1,
            2:,
            1:-1,
        ],
        center,
    )

    y_minus = np.where(
        padded_mask[
            1:-1,
            :-2,
            1:-1,
        ],
        padded_field[
            1:-1,
            :-2,
            1:-1,
        ],
        center,
    )

    z_plus = np.where(
        padded_mask[
            1:-1,
            1:-1,
            2:,
        ],
        padded_field[
            1:-1,
            1:-1,
            2:,
        ],
        center,
    )

    z_minus = np.where(
        padded_mask[
            1:-1,
            1:-1,
            :-2,
        ],
        padded_field[
            1:-1,
            1:-1,
            :-2,
        ],
        center,
    )

    result = (
        (
            x_plus
            - 2.0 * center
            + x_minus
        )
        / dx**2
        + (
            y_plus
            - 2.0 * center
            + y_minus
        )
        / dy**2
        + (
            z_plus
            - 2.0 * center
            + z_minus
        )
        / dz**2
    )

    result[~mask] = 0.0

    return result


def explicit_stability_limit(
    params: ReactionDiffusionParameters,
    spacing: tuple[float, float, float],
    *,
    kill_rate: float = 0.0,
) -> float:
    if any(value <= 0 for value in spacing):
        raise ValueError(
            "Spacing values must be positive"
        )

    if kill_rate < 0:
        raise ValueError(
            "Kill rate must be non-negative"
        )

    dx, dy, dz = spacing

    diffusion_rate = (
        2.0
        * params.diffusion
        * (
            1.0 / dx**2
            + 1.0 / dy**2
            + 1.0 / dz**2
        )
    )

    total_rate = (
        diffusion_rate
        + params.proliferation
        + kill_rate
    )

    if total_rate == 0:
        return float("inf")

    return 1.0 / total_rate


def reaction_diffusion_step(
    field: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    dt: float,
    domain_mask: np.ndarray | None = None,
    treatment: TreatmentWindow | None = None,
    time_day: float = 0.0,
) -> np.ndarray:
    if dt <= 0:
        raise ValueError(
            "dt must be positive"
        )

    if time_day < 0:
        raise ValueError(
            "time_day must be non-negative"
        )

    if field.ndim != 3:
        raise ValueError(
            f"Expected 3D field, got shape {field.shape}"
        )

    kill_rate = 0.0

    if treatment is not None:
        kill_rate = treatment.kill_rate_at(
            time_day
        )

    stability_limit = explicit_stability_limit(
        params,
        spacing,
        kill_rate=kill_rate,
    )

    if dt > stability_limit:
        raise ValueError(
            f"dt={dt} exceeds explicit stability limit "
            f"{stability_limit:.6g}"
        )

    if domain_mask is None:
        laplacian = laplacian_3d(
            field,
            spacing,
        )

        active_field = field

    else:
        if domain_mask.shape != field.shape:
            raise ValueError(
                f"Domain mask shape "
                f"{domain_mask.shape} "
                f"does not match field shape "
                f"{field.shape}"
            )

        active_field = np.where(
            domain_mask,
            field,
            0.0,
        )

        laplacian = masked_laplacian_3d(
            active_field,
            domain_mask,
            spacing,
        )

    diffusion_term = (
        params.diffusion
        * laplacian
    )

    reaction_term = (
        params.proliferation
        * active_field
        * (
            1.0
            - active_field
        )
    )

    treatment_term = (
        kill_rate
        * active_field
    )

    result = (
        active_field
        + dt
        * (
            diffusion_term
            + reaction_term
            - treatment_term
        )
    )

    if domain_mask is not None:
        result[
            ~domain_mask.astype(bool)
        ] = 0.0

    return result


def _same_time(
    first: float,
    second: float,
) -> bool:
    return math.isclose(
        first,
        second,
        rel_tol=0.0,
        abs_tol=_TOLERANCE,
    )


def _continuous_treatment(
    treatment: (
        TreatmentWindow
        | FractionatedRadiotherapy
        | None
    ),
) -> TreatmentWindow | None:
    if isinstance(
        treatment,
        TreatmentWindow,
    ):
        return treatment

    return None


def _fractionated_treatment(
    treatment: (
        TreatmentWindow
        | FractionatedRadiotherapy
        | None
    ),
) -> FractionatedRadiotherapy | None:
    if isinstance(
        treatment,
        FractionatedRadiotherapy,
    ):
        return treatment

    return None


def _apply_fraction_if_due(
    field: np.ndarray,
    *,
    treatment: FractionatedRadiotherapy | None,
    time_day: float,
) -> np.ndarray:
    if treatment is None:
        return field

    if not treatment.has_fraction_at(
        time_day,
        tolerance=_TOLERANCE,
    ):
        return field

    survival_fraction = (
        treatment
        .survival_fraction_per_fraction
    )

    return (
        field
        * survival_fraction
    )


def _next_treatment_boundary(
    *,
    current_time_day: float,
    proposed_end_day: float,
    treatment: (
        TreatmentWindow
        | FractionatedRadiotherapy
        | None
    ),
) -> float | None:
    candidates: list[float] = []

    if isinstance(
        treatment,
        TreatmentWindow,
    ):
        boundaries = (
            treatment.start_day,
            treatment.end_day,
        )

        for boundary in boundaries:
            if (
                boundary > current_time_day
                and not _same_time(
                    boundary,
                    current_time_day,
                )
                and (
                    boundary < proposed_end_day
                    or _same_time(
                        boundary,
                        proposed_end_day,
                    )
                )
            ):
                candidates.append(
                    boundary
                )

    elif isinstance(
        treatment,
        FractionatedRadiotherapy,
    ):
        for fraction_day in (
            treatment.fraction_days
        ):
            if (
                fraction_day > current_time_day
                and not _same_time(
                    fraction_day,
                    current_time_day,
                )
                and (
                    fraction_day < proposed_end_day
                    or _same_time(
                        fraction_day,
                        proposed_end_day,
                    )
                )
            ):
                candidates.append(
                    fraction_day
                )

    if not candidates:
        return None

    return min(
        candidates
    )


def simulate_reaction_diffusion(
    initial_field: np.ndarray,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    domain_mask: np.ndarray | None = None,
    treatment: (
        TreatmentWindow
        | FractionatedRadiotherapy
        | None
    ) = None,
    start_time_day: float = 0.0,
) -> np.ndarray:
    if duration_days < 0:
        raise ValueError(
            "duration_days must be non-negative"
        )

    if dt <= 0:
        raise ValueError(
            "dt must be positive"
        )

    if start_time_day < 0:
        raise ValueError(
            "start_time_day must be non-negative"
        )

    field = np.asarray(
        initial_field,
        dtype=float,
    ).copy()

    if field.ndim != 3:
        raise ValueError(
            f"Expected 3D initial field, "
            f"got shape {field.shape}"
        )

    if (
        np.any(field < 0)
        or np.any(field > 1)
    ):
        raise ValueError(
            "Initial concentration must be "
            "within [0, 1]"
        )

    if (
        domain_mask is not None
        and domain_mask.shape != field.shape
    ):
        raise ValueError(
            f"Domain mask shape "
            f"{domain_mask.shape} "
            f"does not match field shape "
            f"{field.shape}"
        )

    if duration_days == 0:
        return field

    continuous_treatment = (
        _continuous_treatment(
            treatment
        )
    )

    fractionated_treatment = (
        _fractionated_treatment(
            treatment
        )
    )

    elapsed_time = 0.0

    current_time_day = (
        start_time_day
    )

    field = _apply_fraction_if_due(
        field,
        treatment=fractionated_treatment,
        time_day=current_time_day,
    )

    while elapsed_time < duration_days:
        remaining_time = (
            duration_days
            - elapsed_time
        )

        proposed_dt = min(
            dt,
            remaining_time,
        )

        current_time_day = (
            start_time_day
            + elapsed_time
        )

        proposed_end_day = (
            current_time_day
            + proposed_dt
        )

        boundary = _next_treatment_boundary(
            current_time_day=current_time_day,
            proposed_end_day=proposed_end_day,
            treatment=treatment,
        )

        if boundary is None:
            step_dt = proposed_dt
        else:
            step_dt = (
                boundary
                - current_time_day
            )

        field = reaction_diffusion_step(
            field,
            params,
            spacing=spacing,
            dt=step_dt,
            domain_mask=domain_mask,
            treatment=continuous_treatment,
            time_day=current_time_day,
        )

        elapsed_time += step_dt

        new_time_day = (
            start_time_day
            + elapsed_time
        )

        field = _apply_fraction_if_due(
            field,
            treatment=(
                fractionated_treatment
            ),
            time_day=new_time_day,
        )

    return field