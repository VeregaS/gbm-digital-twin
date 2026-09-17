from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import (
    explicit_stability_limit,
    laplacian_3d,
    masked_laplacian_3d,
)
from gbm_twin.models.spatial_radiotherapy import apply_spatial_pirt_fraction

SurvivalValue = float | np.ndarray


@dataclass(frozen=True)
class FractionResponseEvent:
    day: float
    immediate_survival: SurvivalValue
    proliferation_survival: SurvivalValue = 1.0

    def __post_init__(self) -> None:
        if self.day < 0.0:
            raise ValueError("fraction response day must be non-negative")


@dataclass(frozen=True)
class TreatmentMemoryState:
    field: np.ndarray
    proliferation_modifier: np.ndarray

    def __post_init__(self) -> None:
        if self.field.ndim != 3:
            raise ValueError("field must be 3D")

        if self.proliferation_modifier.shape != self.field.shape:
            raise ValueError(
                "proliferation_modifier must match field shape"
            )

        if np.any(self.field < 0.0) or np.any(self.field > 1.0):
            raise ValueError("field must be within [0, 1]")

        if (
            np.any(self.proliferation_modifier < 0.0)
            or np.any(self.proliferation_modifier > 1.0)
        ):
            raise ValueError(
                "proliferation_modifier must be within [0, 1]"
            )


def initial_treatment_memory_state(
    field: np.ndarray,
    *,
    domain_mask: np.ndarray | None = None,
) -> TreatmentMemoryState:
    source = np.asarray(field, dtype=np.float32).copy()

    if source.ndim != 3:
        raise ValueError("field must be 3D")

    if np.any(source < 0.0) or np.any(source > 1.0):
        raise ValueError("field must be within [0, 1]")

    modifier = np.ones_like(source, dtype=np.float32)

    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)

        if domain.shape != source.shape:
            raise ValueError("domain_mask must match field shape")

        source[~domain] = 0.0
        modifier[~domain] = 0.0

    return TreatmentMemoryState(
        field=source,
        proliferation_modifier=modifier,
    )


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
        scalar = float(value)
        result = np.full(shape, scalar, dtype=np.float32)

    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite values")

    if np.any(result < 0.0) or np.any(result > 1.0):
        raise ValueError(f"{name} must be within [0, 1]")

    return result


def apply_fraction_response(
    state: TreatmentMemoryState,
    event: FractionResponseEvent,
    *,
    domain_mask: np.ndarray | None = None,
) -> TreatmentMemoryState:
    immediate = _survival_field(
        event.immediate_survival,
        shape=state.field.shape,
        name="immediate_survival",
    )
    proliferative = _survival_field(
        event.proliferation_survival,
        shape=state.field.shape,
        name="proliferation_survival",
    )

    field = apply_spatial_pirt_fraction(
        state.field,
        survival_fraction=immediate,
        domain_mask=domain_mask,
    )

    modifier = np.asarray(
        state.proliferation_modifier * proliferative,
        dtype=np.float32,
    )
    np.clip(modifier, 0.0, 1.0, out=modifier)

    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)

        if domain.shape != field.shape:
            raise ValueError("domain_mask must match state shape")

        modifier[~domain] = 0.0

    return TreatmentMemoryState(
        field=np.asarray(field, dtype=np.float32),
        proliferation_modifier=modifier,
    )


def assimilate_observed_density(
    state: TreatmentMemoryState,
    observed_density: np.ndarray,
    *,
    observation_weight: float = 1.0,
    domain_mask: np.ndarray | None = None,
) -> TreatmentMemoryState:
    """Assimilate an MRI-derived density field without erasing RT memory."""

    if not 0.0 <= observation_weight <= 1.0:
        raise ValueError("observation_weight must be within [0, 1]")

    observed = np.asarray(observed_density, dtype=np.float32)

    if observed.shape != state.field.shape:
        raise ValueError("observed_density must match state shape")

    if np.any(observed < 0.0) or np.any(observed > 1.0):
        raise ValueError("observed_density must be within [0, 1]")

    field = (
        observation_weight * observed
        + (1.0 - observation_weight) * state.field
    ).astype(np.float32, copy=False)

    modifier = state.proliferation_modifier.copy()

    if domain_mask is not None:
        domain = np.asarray(domain_mask, dtype=bool)

        if domain.shape != field.shape:
            raise ValueError("domain_mask must match state shape")

        field[~domain] = 0.0
        modifier[~domain] = 0.0

    return TreatmentMemoryState(
        field=field,
        proliferation_modifier=modifier,
    )


def treatment_memory_step(
    state: TreatmentMemoryState,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    dt: float,
    domain_mask: np.ndarray | None = None,
) -> TreatmentMemoryState:
    if dt <= 0.0:
        raise ValueError("dt must be positive")

    limit = explicit_stability_limit(params, spacing)

    if dt > limit:
        raise ValueError(
            f"dt={dt} exceeds explicit stability limit {limit:.6g}"
        )

    field = np.asarray(state.field, dtype=np.float32)
    modifier = np.asarray(
        state.proliferation_modifier,
        dtype=np.float32,
    )

    domain: np.ndarray | None = None

    if domain_mask is None:
        laplacian = laplacian_3d(field, spacing)
    else:
        domain = np.asarray(domain_mask, dtype=bool)

        if domain.shape != field.shape:
            raise ValueError("domain_mask must match state shape")

        laplacian = masked_laplacian_3d(field, domain, spacing)

    diffusion = params.diffusion * laplacian
    reaction = (
        params.proliferation
        * modifier
        * field
        * (1.0 - field)
    )

    updated = field + dt * (diffusion + reaction)
    np.clip(updated, 0.0, 1.0, out=updated)

    if domain is not None:
        updated[~domain] = 0.0

    return TreatmentMemoryState(
        field=np.asarray(updated, dtype=np.float32),
        proliferation_modifier=modifier.copy(),
    )


def simulate_with_treatment_memory(
    initial_state: TreatmentMemoryState,
    params: ReactionDiffusionParameters,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    start_time_day: float = 0.0,
    fraction_events: tuple[FractionResponseEvent, ...] = (),
    domain_mask: np.ndarray | None = None,
) -> TreatmentMemoryState:
    if duration_days < 0.0:
        raise ValueError("duration_days must be non-negative")

    if start_time_day < 0.0:
        raise ValueError("start_time_day must be non-negative")

    ordered = tuple(sorted(fraction_events, key=lambda item: item.day))

    if len({event.day for event in ordered}) != len(ordered):
        raise ValueError("fraction_events must have unique days")

    end_time_day = start_time_day + duration_days

    for event in ordered:
        if event.day < start_time_day or event.day > end_time_day:
            raise ValueError(
                "fraction event lies outside the simulated interval"
            )

    state = TreatmentMemoryState(
        field=initial_state.field.copy(),
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
            state = apply_fraction_response(
                state,
                ordered[event_index],
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

        state = treatment_memory_step(
            state,
            params,
            spacing=spacing,
            dt=step_dt,
            domain_mask=domain_mask,
        )
        current = step_end

    while event_index < len(ordered):
        event = ordered[event_index]

        if abs(event.day - end_time_day) > tolerance:
            break

        state = apply_fraction_response(
            state,
            event,
            domain_mask=domain_mask,
        )
        event_index += 1

    return state
