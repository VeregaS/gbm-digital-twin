from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import (
    explicit_stability_limit,
    laplacian_3d,
    masked_laplacian_3d,
)

SurvivalValue = float | np.ndarray


@dataclass(frozen=True)
class DelayedResponseParameters:
    """Global delayed-response parameters for the Stage 9 ablation family."""

    damage_transfer_fraction: float
    damage_half_life_days: float
    damaged_visibility: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.damage_transfer_fraction <= 1.0:
            raise ValueError(
                "damage_transfer_fraction must be within [0, 1]"
            )
        if (
            not math.isfinite(self.damage_half_life_days)
            or self.damage_half_life_days <= 0.0
        ):
            raise ValueError(
                "damage_half_life_days must be finite and positive"
            )
        if not 0.0 <= self.damaged_visibility <= 1.0:
            raise ValueError("damaged_visibility must be within [0, 1]")


@dataclass(frozen=True)
class DelayedResponseEvent:
    day: float
    immediate_survival: SurvivalValue
    proliferation_survival: SurvivalValue = 1.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.day) or self.day < 0.0:
            raise ValueError("event day must be finite and non-negative")


@dataclass(frozen=True)
class DelayedResponseState:
    """Viable, treatment-damaged, and persistent proliferation states."""

    viable: np.ndarray
    damaged: np.ndarray
    proliferation_modifier: np.ndarray

    def __post_init__(self) -> None:
        if self.viable.ndim != 3:
            raise ValueError("viable field must be 3D")
        if self.damaged.shape != self.viable.shape:
            raise ValueError("damaged field must match viable field")
        if self.proliferation_modifier.shape != self.viable.shape:
            raise ValueError(
                "proliferation_modifier must match viable field"
            )

        for value, name in (
            (self.viable, "viable"),
            (self.damaged, "damaged"),
            (self.proliferation_modifier, "proliferation_modifier"),
        ):
            if not np.all(np.isfinite(value)):
                raise ValueError(f"{name} must contain finite values")
            if np.any(value < 0.0) or np.any(value > 1.0):
                raise ValueError(f"{name} must be within [0, 1]")

        if np.any(self.viable + self.damaged > 1.0 + 1e-6):
            raise ValueError(
                "viable + damaged occupancy must not exceed 1"
            )


def initial_delayed_response_state(
    visible_density: np.ndarray,
    *,
    domain_mask: np.ndarray | None = None,
) -> DelayedResponseState:
    viable = np.asarray(visible_density, dtype=np.float32).copy()
    if viable.ndim != 3:
        raise ValueError("visible_density must be 3D")
    if not np.all(np.isfinite(viable)):
        raise ValueError("visible_density must contain finite values")
    if np.any(viable < 0.0) or np.any(viable > 1.0):
        raise ValueError("visible_density must be within [0, 1]")

    damaged = np.zeros_like(viable, dtype=np.float32)
    modifier = np.ones_like(viable, dtype=np.float32)

    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)
        if domain.shape != viable.shape:
            raise ValueError("domain_mask must match visible_density")
        viable[~domain] = 0.0
        modifier[~domain] = 0.0

    return DelayedResponseState(
        viable=viable,
        damaged=damaged,
        proliferation_modifier=modifier,
    )


def visible_density(
    state: DelayedResponseState,
    parameters: DelayedResponseParameters,
) -> np.ndarray:
    """Map latent compartments to the MRI-visible tumor-density surrogate."""

    visible = (
        np.asarray(state.viable, dtype=np.float32)
        + parameters.damaged_visibility
        * np.asarray(state.damaged, dtype=np.float32)
    )
    np.clip(visible, 0.0, 1.0, out=visible)
    return visible.astype(np.float32, copy=False)


def _survival_field(
    value: SurvivalValue,
    *,
    shape: tuple[int, ...],
    name: str,
) -> np.ndarray:
    if isinstance(value, np.ndarray):
        result = np.asarray(value, dtype=np.float32)
        if result.shape != shape:
            raise ValueError(f"{name} must match state shape")
    else:
        result = np.full(shape, float(value), dtype=np.float32)

    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite values")
    if np.any(result < 0.0) or np.any(result > 1.0):
        raise ValueError(f"{name} must be within [0, 1]")
    return result


def apply_delayed_fraction_response(
    state: DelayedResponseState,
    event: DelayedResponseEvent,
    *,
    parameters: DelayedResponseParameters,
    domain_mask: np.ndarray | None = None,
) -> DelayedResponseState:
    """Apply PIRT loss while transferring a fraction into damaged cells.

    A zero transfer fraction is an exact structural ablation of the delayed
    compartment: the viable-cell update reduces to the Stage 8 PIRT loss.
    """

    survival = _survival_field(
        event.immediate_survival,
        shape=state.viable.shape,
        name="immediate_survival",
    )
    proliferation_survival = _survival_field(
        event.proliferation_survival,
        shape=state.viable.shape,
        name="proliferation_survival",
    )

    viable = np.asarray(state.viable, dtype=np.float32)
    loss = (1.0 - survival) * viable * (1.0 - viable)

    domain: np.ndarray | None = None
    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)
        if domain.shape != viable.shape:
            raise ValueError("domain_mask must match state shape")
        loss = np.where(domain, loss, 0.0)

    updated_viable = viable - loss
    updated_damaged = (
        np.asarray(state.damaged, dtype=np.float32)
        + parameters.damage_transfer_fraction * loss
    )
    modifier = (
        np.asarray(state.proliferation_modifier, dtype=np.float32)
        * proliferation_survival
    )

    np.clip(updated_viable, 0.0, 1.0, out=updated_viable)
    np.clip(updated_damaged, 0.0, 1.0, out=updated_damaged)
    np.clip(modifier, 0.0, 1.0, out=modifier)

    if domain is not None:
        updated_viable[~domain] = 0.0
        updated_damaged[~domain] = 0.0
        modifier[~domain] = 0.0

    return DelayedResponseState(
        viable=np.asarray(updated_viable, dtype=np.float32),
        damaged=np.asarray(updated_damaged, dtype=np.float32),
        proliferation_modifier=np.asarray(modifier, dtype=np.float32),
    )


def assimilate_visible_density(
    state: DelayedResponseState,
    observed_density: np.ndarray,
    *,
    parameters: DelayedResponseParameters,
    domain_mask: np.ndarray | None = None,
) -> DelayedResponseState:
    """Assimilate MRI while retaining all damaged burden compatible with it.

    The damaged compartment is latent. At assimilation we preserve it unless
    its MRI-visible contribution alone would exceed the observed density.
    This avoids both erasing treatment memory and retaining a state that is
    already inconsistent with the measured t1 observation.
    """

    observed = np.asarray(observed_density, dtype=np.float32)
    if observed.shape != state.viable.shape:
        raise ValueError("observed_density must match state shape")
    if not np.all(np.isfinite(observed)):
        raise ValueError("observed_density must contain finite values")
    if np.any(observed < 0.0) or np.any(observed > 1.0):
        raise ValueError("observed_density must be within [0, 1]")

    damaged = np.asarray(state.damaged, dtype=np.float32).copy()
    visibility = parameters.damaged_visibility

    if visibility > 0.0:
        compatible_damaged = observed / visibility
        damaged = np.minimum(damaged, compatible_damaged)

    viable = observed - visibility * damaged
    viable = np.minimum(viable, 1.0 - damaged)
    np.clip(viable, 0.0, 1.0, out=viable)

    modifier = np.asarray(
        state.proliferation_modifier,
        dtype=np.float32,
    ).copy()

    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)
        if domain.shape != viable.shape:
            raise ValueError("domain_mask must match state shape")
        viable[~domain] = 0.0
        damaged[~domain] = 0.0
        modifier[~domain] = 0.0

    return DelayedResponseState(
        viable=viable.astype(np.float32, copy=False),
        damaged=damaged.astype(np.float32, copy=False),
        proliferation_modifier=modifier,
    )


def delayed_response_step(
    state: DelayedResponseState,
    growth: ReactionDiffusionParameters,
    *,
    delayed: DelayedResponseParameters,
    spacing: tuple[float, float, float],
    dt: float,
    domain_mask: np.ndarray | None = None,
) -> DelayedResponseState:
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    stability_limit = explicit_stability_limit(growth, spacing)
    if dt > stability_limit:
        raise ValueError(
            f"dt={dt} exceeds explicit stability limit "
            f"{stability_limit:.6g}"
        )

    viable = np.asarray(state.viable, dtype=np.float32)
    damaged = np.asarray(state.damaged, dtype=np.float32)
    modifier = np.asarray(
        state.proliferation_modifier,
        dtype=np.float32,
    )

    domain: np.ndarray | None = None
    if domain_mask is None:
        laplacian = laplacian_3d(viable, spacing)
    else:
        domain = np.asarray(domain_mask, dtype=bool)
        if domain.shape != viable.shape:
            raise ValueError("domain_mask must match state shape")
        laplacian = masked_laplacian_3d(
            viable,
            domain,
            spacing,
        )

    occupancy = np.clip(viable + damaged, 0.0, 1.0)
    reaction = (
        growth.proliferation
        * modifier
        * viable
        * (1.0 - occupancy)
    )
    updated_viable = (
        viable
        + dt * (growth.diffusion * laplacian + reaction)
    )
    np.clip(updated_viable, 0.0, 1.0, out=updated_viable)

    decay_rate = math.log(2.0) / delayed.damage_half_life_days
    updated_damaged = damaged * math.exp(-decay_rate * dt)
    np.clip(updated_damaged, 0.0, 1.0, out=updated_damaged)

    total = updated_viable + updated_damaged
    overflow = total > 1.0
    if np.any(overflow):
        updated_viable[overflow] = np.maximum(
            0.0,
            1.0 - updated_damaged[overflow],
        )

    if domain is not None:
        updated_viable[~domain] = 0.0
        updated_damaged[~domain] = 0.0

    return DelayedResponseState(
        viable=np.asarray(updated_viable, dtype=np.float32),
        damaged=np.asarray(updated_damaged, dtype=np.float32),
        proliferation_modifier=modifier.copy(),
    )


def simulate_delayed_response(
    initial_state: DelayedResponseState,
    growth: ReactionDiffusionParameters,
    *,
    delayed: DelayedResponseParameters,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    start_time_day: float = 0.0,
    events: tuple[DelayedResponseEvent, ...] = (),
    domain_mask: np.ndarray | None = None,
) -> DelayedResponseState:
    if duration_days < 0.0:
        raise ValueError("duration_days must be non-negative")
    if start_time_day < 0.0:
        raise ValueError("start_time_day must be non-negative")

    ordered = tuple(sorted(events, key=lambda item: item.day))
    if len({event.day for event in ordered}) != len(ordered):
        raise ValueError("events must have unique days")

    end_time_day = start_time_day + duration_days
    for event in ordered:
        if event.day < start_time_day or event.day > end_time_day:
            raise ValueError("event lies outside the simulated interval")

    state = DelayedResponseState(
        viable=initial_state.viable.copy(),
        damaged=initial_state.damaged.copy(),
        proliferation_modifier=(
            initial_state.proliferation_modifier.copy()
        ),
    )
    current = start_time_day
    event_index = 0
    tolerance = 1e-9

    while current < end_time_day - tolerance:
        next_event_day = (
            ordered[event_index].day
            if event_index < len(ordered)
            else None
        )

        if (
            next_event_day is not None
            and abs(next_event_day - current) <= tolerance
        ):
            state = apply_delayed_fraction_response(
                state,
                ordered[event_index],
                parameters=delayed,
                domain_mask=domain_mask,
            )
            event_index += 1
            continue

        step_end = min(current + dt, end_time_day)
        if next_event_day is not None and next_event_day < step_end:
            step_end = next_event_day

        step_dt = step_end - current
        if step_dt <= tolerance:
            current = step_end
            continue

        state = delayed_response_step(
            state,
            growth,
            delayed=delayed,
            spacing=spacing,
            dt=step_dt,
            domain_mask=domain_mask,
        )
        current = step_end

    while event_index < len(ordered):
        event = ordered[event_index]
        if abs(event.day - end_time_day) > tolerance:
            break
        state = apply_delayed_fraction_response(
            state,
            event,
            parameters=delayed,
            domain_mask=domain_mask,
        )
        event_index += 1

    return state
