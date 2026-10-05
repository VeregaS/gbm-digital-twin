from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import (
    explicit_stability_limit,
    laplacian_3d,
    masked_laplacian_3d,
    validate_simulation_timing,
)

SurvivalValue = float | np.ndarray


@dataclass(frozen=True)
class DecoupledDamageParameters:
    """Stage 10 fixed-structure parameters.

    Only the MRI-visible damaged-state half-life is varied in the predefined
    diagnostic. Damage transfer, damaged visibility and inert retention are
    deliberately fixed to one by construction.
    """

    damage_half_life_days: float

    def __post_init__(self) -> None:
        if (
            not math.isfinite(
                self.damage_half_life_days
            )
            or self.damage_half_life_days
            <= 0.0
        ):
            raise ValueError(
                "damage_half_life_days must be finite and positive"
            )


@dataclass(frozen=True)
class DecoupledDamageEvent:
    day: float
    immediate_survival: SurvivalValue
    proliferation_survival: SurvivalValue = 1.0

    def __post_init__(self) -> None:
        if (
            not math.isfinite(
                self.day
            )
            or self.day < 0.0
        ):
            raise ValueError(
                "event day must be finite and non-negative"
            )


@dataclass(frozen=True)
class DecoupledDamageState:
    viable: np.ndarray
    damaged: np.ndarray
    inert: np.ndarray
    proliferation_modifier: np.ndarray

    def __post_init__(self) -> None:
        if self.viable.ndim != 3:
            raise ValueError(
                "viable field must be 3D"
            )

        for value, name in (
            (
                self.damaged,
                "damaged",
            ),
            (
                self.inert,
                "inert",
            ),
            (
                self.proliferation_modifier,
                "proliferation_modifier",
            ),
        ):
            if value.shape != self.viable.shape:
                raise ValueError(
                    f"{name} field must match viable field"
                )

        for value, name in (
            (
                self.viable,
                "viable",
            ),
            (
                self.damaged,
                "damaged",
            ),
            (
                self.inert,
                "inert",
            ),
            (
                self.proliferation_modifier,
                "proliferation_modifier",
            ),
        ):
            if not np.all(
                np.isfinite(
                    value
                )
            ):
                raise ValueError(
                    f"{name} must contain finite values"
                )

            if (
                np.any(
                    value < 0.0
                )
                or np.any(
                    value > 1.0
                )
            ):
                raise ValueError(
                    f"{name} must be within [0, 1]"
                )

        occupancy = (
            self.viable
            + self.damaged
            + self.inert
        )

        if np.any(
            occupancy > 1.0 + 1e-6
        ):
            raise ValueError(
                "viable + damaged + inert occupancy must not exceed 1"
            )


def initial_decoupled_damage_state(
    visible_density: np.ndarray,
    *,
    domain_mask: np.ndarray | None = None,
) -> DecoupledDamageState:
    viable = np.asarray(
        visible_density,
        dtype=np.float32,
    ).copy()

    if viable.ndim != 3:
        raise ValueError(
            "visible_density must be 3D"
        )

    if not np.all(
        np.isfinite(
            viable
        )
    ):
        raise ValueError(
            "visible_density must contain finite values"
        )

    if (
        np.any(
            viable < 0.0
        )
        or np.any(
            viable > 1.0
        )
    ):
        raise ValueError(
            "visible_density must be within [0, 1]"
        )

    damaged = np.zeros_like(
        viable,
        dtype=np.float32,
    )

    inert = np.zeros_like(
        viable,
        dtype=np.float32,
    )

    modifier = np.ones_like(
        viable,
        dtype=np.float32,
    )

    if domain_mask is not None:
        domain = np.asarray(
            domain_mask,
            dtype=bool,
        )

        if domain.shape != viable.shape:
            raise ValueError(
                "domain_mask must match visible_density"
            )

        viable[~domain] = 0.0
        modifier[~domain] = 0.0

    return DecoupledDamageState(
        viable=viable,
        damaged=damaged,
        inert=inert,
        proliferation_modifier=modifier,
    )


def visible_density(
    state: DecoupledDamageState,
) -> np.ndarray:
    visible = (
        np.asarray(
            state.viable,
            dtype=np.float32,
        )
        + np.asarray(
            state.damaged,
            dtype=np.float32,
        )
    )

    np.clip(
        visible,
        0.0,
        1.0,
        out=visible,
    )

    return visible.astype(
        np.float32,
        copy=False,
    )


def _survival_field(
    value: SurvivalValue,
    *,
    shape: tuple[int, ...],
    name: str,
) -> np.ndarray:
    if isinstance(
        value,
        np.ndarray,
    ):
        result = np.asarray(
            value,
            dtype=np.float32,
        )

        if result.shape != shape:
            raise ValueError(
                f"{name} must match state shape"
            )

    else:
        result = np.full(
            shape,
            float(
                value
            ),
            dtype=np.float32,
        )

    if not np.all(
        np.isfinite(
            result
        )
    ):
        raise ValueError(
            f"{name} must contain finite values"
        )

    if (
        np.any(
            result < 0.0
        )
        or np.any(
            result > 1.0
        )
    ):
        raise ValueError(
            f"{name} must be within [0, 1]"
        )

    return result


def apply_decoupled_fraction_response(
    state: DecoupledDamageState,
    event: DecoupledDamageEvent,
    *,
    domain_mask: np.ndarray | None = None,
) -> DecoupledDamageState:
    survival = _survival_field(
        event.immediate_survival,
        shape=state.viable.shape,
        name="immediate_survival",
    )

    proliferation_survival = (
        _survival_field(
            event.proliferation_survival,
            shape=state.viable.shape,
            name="proliferation_survival",
        )
    )

    viable = np.asarray(
        state.viable,
        dtype=np.float32,
    )

    loss = (
        (1.0 - survival)
        * viable
        * (1.0 - viable)
    )

    domain: np.ndarray | None = None

    if domain_mask is not None:
        domain = np.asarray(
            domain_mask,
            dtype=bool,
        )

        if domain.shape != viable.shape:
            raise ValueError(
                "domain_mask must match state shape"
            )

        loss = np.where(
            domain,
            loss,
            0.0,
        )

    updated_viable = (
        viable
        - loss
    )

    updated_damaged = (
        np.asarray(
            state.damaged,
            dtype=np.float32,
        )
        + loss
    )

    updated_inert = np.asarray(
        state.inert,
        dtype=np.float32,
    ).copy()

    modifier = (
        np.asarray(
            state.proliferation_modifier,
            dtype=np.float32,
        )
        * proliferation_survival
    )

    for value in (
        updated_viable,
        updated_damaged,
        updated_inert,
        modifier,
    ):
        np.clip(
            value,
            0.0,
            1.0,
            out=value,
        )

    if domain is not None:
        updated_viable[~domain] = 0.0
        updated_damaged[~domain] = 0.0
        updated_inert[~domain] = 0.0
        modifier[~domain] = 0.0

    return DecoupledDamageState(
        viable=np.asarray(
            updated_viable,
            dtype=np.float32,
        ),
        damaged=np.asarray(
            updated_damaged,
            dtype=np.float32,
        ),
        inert=np.asarray(
            updated_inert,
            dtype=np.float32,
        ),
        proliferation_modifier=np.asarray(
            modifier,
            dtype=np.float32,
        ),
    )


def assimilate_visible_density(
    state: DecoupledDamageState,
    observed_density: np.ndarray,
    *,
    domain_mask: np.ndarray | None = None,
) -> DecoupledDamageState:
    """Assimilate t1 while preserving compatible treatment memory.

    Stage 10 fixes damaged visibility to one. Therefore visible density is
    v + d, while q is MRI-invisible occupancy. We retain as much d as the
    observation permits, retain q up to the remaining carrying capacity,
    assign the rest of the visible observation to v, and preserve m.
    """

    observed = np.asarray(
        observed_density,
        dtype=np.float32,
    )

    if observed.shape != state.viable.shape:
        raise ValueError(
            "observed_density must match state shape"
        )

    if not np.all(
        np.isfinite(
            observed
        )
    ):
        raise ValueError(
            "observed_density must contain finite values"
        )

    if (
        np.any(
            observed < 0.0
        )
        or np.any(
            observed > 1.0
        )
    ):
        raise ValueError(
            "observed_density must be within [0, 1]"
        )

    damaged = np.minimum(
        np.asarray(
            state.damaged,
            dtype=np.float32,
        ),
        observed,
    )

    inert_capacity = (
        1.0
        - observed
    )

    inert = np.minimum(
        np.asarray(
            state.inert,
            dtype=np.float32,
        ),
        inert_capacity,
    )

    viable = (
        observed
        - damaged
    )

    modifier = np.asarray(
        state.proliferation_modifier,
        dtype=np.float32,
    ).copy()

    np.clip(
        viable,
        0.0,
        1.0,
        out=viable,
    )

    np.clip(
        damaged,
        0.0,
        1.0,
        out=damaged,
    )

    np.clip(
        inert,
        0.0,
        1.0,
        out=inert,
    )

    if domain_mask is not None:
        domain = np.asarray(
            domain_mask,
            dtype=bool,
        )

        if domain.shape != viable.shape:
            raise ValueError(
                "domain_mask must match state shape"
            )

        viable[~domain] = 0.0
        damaged[~domain] = 0.0
        inert[~domain] = 0.0
        modifier[~domain] = 0.0

    return DecoupledDamageState(
        viable=viable.astype(
            np.float32,
            copy=False,
        ),
        damaged=damaged.astype(
            np.float32,
            copy=False,
        ),
        inert=inert.astype(
            np.float32,
            copy=False,
        ),
        proliferation_modifier=modifier,
    )


def decoupled_damage_step(
    state: DecoupledDamageState,
    growth: ReactionDiffusionParameters,
    *,
    parameters: DecoupledDamageParameters,
    spacing: tuple[
        float,
        float,
        float,
    ],
    dt: float,
    domain_mask: np.ndarray | None = None,
) -> DecoupledDamageState:
    if dt <= 0.0:
        raise ValueError(
            "dt must be positive"
        )

    stability_limit = (
        explicit_stability_limit(
            growth,
            spacing,
        )
    )

    if dt > stability_limit:
        raise ValueError(
            f"dt={dt} exceeds explicit stability limit "
            f"{stability_limit:.6g}"
        )

    viable = np.asarray(
        state.viable,
        dtype=np.float32,
    )

    damaged = np.asarray(
        state.damaged,
        dtype=np.float32,
    )

    inert = np.asarray(
        state.inert,
        dtype=np.float32,
    )

    modifier = np.asarray(
        state.proliferation_modifier,
        dtype=np.float32,
    )

    domain: np.ndarray | None = None

    if domain_mask is None:
        laplacian = laplacian_3d(
            viable,
            spacing,
        )

    else:
        domain = np.asarray(
            domain_mask,
            dtype=bool,
        )

        if domain.shape != viable.shape:
            raise ValueError(
                "domain_mask must match state shape"
            )

        laplacian = (
            masked_laplacian_3d(
                viable,
                domain,
                spacing,
            )
        )

    occupancy = np.clip(
        viable
        + damaged
        + inert,
        0.0,
        1.0,
    )

    reaction = (
        growth.proliferation
        * modifier
        * viable
        * (1.0 - occupancy)
    )

    updated_viable = (
        viable
        + dt
        * (
            growth.diffusion
            * laplacian
            + reaction
        )
    )

    np.clip(
        updated_viable,
        0.0,
        1.0,
        out=updated_viable,
    )

    decay_rate = (
        math.log(
            2.0
        )
        / parameters
        .damage_half_life_days
    )

    updated_damaged = (
        damaged
        * math.exp(
            -decay_rate
            * dt
        )
    )

    cleared_damaged = (
        damaged
        - updated_damaged
    )

    updated_inert = (
        inert
        + cleared_damaged
    )

    np.clip(
        updated_damaged,
        0.0,
        1.0,
        out=updated_damaged,
    )

    np.clip(
        updated_inert,
        0.0,
        1.0,
        out=updated_inert,
    )

    maximum_viable = np.maximum(
        0.0,
        1.0
        - updated_damaged
        - updated_inert,
    )

    updated_viable = np.minimum(
        updated_viable,
        maximum_viable,
    )

    if domain is not None:
        updated_viable[~domain] = 0.0
        updated_damaged[~domain] = 0.0
        updated_inert[~domain] = 0.0

    return DecoupledDamageState(
        viable=np.asarray(
            updated_viable,
            dtype=np.float32,
        ),
        damaged=np.asarray(
            updated_damaged,
            dtype=np.float32,
        ),
        inert=np.asarray(
            updated_inert,
            dtype=np.float32,
        ),
        proliferation_modifier=(
            modifier.copy()
        ),
    )


def simulate_decoupled_damage(
    initial_state: DecoupledDamageState,
    growth: ReactionDiffusionParameters,
    *,
    parameters: DecoupledDamageParameters,
    spacing: tuple[
        float,
        float,
        float,
    ],
    duration_days: float,
    dt: float,
    start_time_day: float = 0.0,
    events: tuple[
        DecoupledDamageEvent,
        ...,
    ] = (),
    domain_mask: np.ndarray | None = None,
) -> DecoupledDamageState:
    validate_simulation_timing(
        duration_days=duration_days, dt=dt, start_time_day=start_time_day,
    )

    ordered = tuple(
        sorted(
            events,
            key=lambda item: item.day,
        )
    )

    if len(
        {
            event.day
            for event in ordered
        }
    ) != len(
        ordered
    ):
        raise ValueError(
            "events must have unique days"
        )

    end_time_day = (
        start_time_day
        + duration_days
    )

    for event in ordered:
        if (
            event.day < start_time_day
            or event.day > end_time_day
        ):
            raise ValueError(
                "event lies outside the simulated interval"
            )

    state = DecoupledDamageState(
        viable=(
            initial_state
            .viable
            .copy()
        ),
        damaged=(
            initial_state
            .damaged
            .copy()
        ),
        inert=(
            initial_state
            .inert
            .copy()
        ),
        proliferation_modifier=(
            initial_state
            .proliferation_modifier
            .copy()
        ),
    )

    current = start_time_day
    event_index = 0
    tolerance = 1e-9

    while (
        current
        < end_time_day
        - tolerance
    ):
        next_event_day = (
            ordered[
                event_index
            ].day
            if (
                event_index
                < len(
                    ordered
                )
            )
            else None
        )

        if (
            next_event_day
            is not None
            and abs(
                next_event_day
                - current
            )
            <= tolerance
        ):
            state = (
                apply_decoupled_fraction_response(
                    state,
                    ordered[
                        event_index
                    ],
                    domain_mask=(
                        domain_mask
                    ),
                )
            )

            event_index += 1
            continue

        step_end = min(
            current + dt,
            end_time_day,
        )

        if (
            next_event_day
            is not None
            and next_event_day
            < step_end
        ):
            step_end = (
                next_event_day
            )

        step_dt = (
            step_end
            - current
        )

        if step_dt <= tolerance:
            current = step_end
            continue

        state = (
            decoupled_damage_step(
                state,
                growth,
                parameters=(
                    parameters
                ),
                spacing=spacing,
                dt=step_dt,
                domain_mask=(
                    domain_mask
                ),
            )
        )

        current = step_end

    while (
        event_index
        < len(
            ordered
        )
    ):
        event = ordered[
            event_index
        ]

        if (
            abs(
                event.day
                - end_time_day
            )
            > tolerance
        ):
            break

        state = (
            apply_decoupled_fraction_response(
                state,
                event,
                domain_mask=(
                    domain_mask
                ),
            )
        )

        event_index += 1

    return state
