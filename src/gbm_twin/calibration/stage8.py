from __future__ import annotations

import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.calibration.diagnostics import (
    CalibrationDiagnostics,
    assess_calibration_diagnostics,
)
from gbm_twin.calibration.grid_search import CalibrationResult
from gbm_twin.calibration.refinement import build_refined_axis
from gbm_twin.evaluation.soft_metrics import (
    soft_dice_score,
    soft_relative_volume_error,
    soft_threshold_membership,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.treatment_memory import (
    FractionResponseEvent,
    TreatmentMemoryState,
    simulate_with_treatment_memory,
)


@dataclass(frozen=True)
class Stage8CalibrationConfig:
    diffusion_values: tuple[float, ...]
    proliferation_values: tuple[float, ...]
    dt_days: float = 2.0
    observation_threshold: float = 0.80
    soft_temperature: float = 0.05
    volume_weight: float = 0.5
    refinement_rounds: int = 3
    upper_boundary_expansion_factor: float = 1.0

    def __post_init__(self) -> None:
        if len(self.diffusion_values) < 2:
            raise ValueError("At least two diffusion values are required")
        if len(self.proliferation_values) < 2:
            raise ValueError("At least two proliferation values are required")
        if any(value < 0.0 for value in self.diffusion_values):
            raise ValueError("diffusion values must be non-negative")
        if any(value < 0.0 for value in self.proliferation_values):
            raise ValueError("proliferation values must be non-negative")
        if self.dt_days <= 0.0:
            raise ValueError("dt_days must be positive")
        if not 0.0 < self.observation_threshold < 1.0:
            raise ValueError("observation_threshold must be within (0, 1)")
        if self.soft_temperature <= 0.0:
            raise ValueError("soft_temperature must be positive")
        if self.volume_weight < 0.0:
            raise ValueError("volume_weight must be non-negative")
        if self.refinement_rounds < 1:
            raise ValueError("refinement_rounds must be at least 1")
        if self.upper_boundary_expansion_factor <= 0.0:
            raise ValueError(
                "upper_boundary_expansion_factor must be positive"
            )


@dataclass(frozen=True)
class Stage8CalibrationRun:
    best: CalibrationResult
    coarse_best: CalibrationResult
    diagnostics: CalibrationDiagnostics
    candidates: tuple[CalibrationResult, ...]
    coarse_candidates: tuple[CalibrationResult, ...]
    refined_candidates: tuple[CalibrationResult, ...]
    cache_signature: str


@dataclass(frozen=True)
class _Candidate:
    diffusion: float
    proliferation: float


@dataclass(frozen=True)
class _GridContext:
    initial_state: TreatmentMemoryState
    observed_mask: np.ndarray
    domain_mask: np.ndarray
    spacing: tuple[float, float, float]
    duration_days: float
    start_time_day: float
    events: tuple[FractionResponseEvent, ...]
    config: Stage8CalibrationConfig
    signature: str
    cache_dir: Path | None
    workers: int


_WORKER_INITIAL_FIELD: np.ndarray | None = None
_WORKER_INITIAL_MODIFIER: np.ndarray | None = None
_WORKER_OBSERVED_MASK: np.ndarray | None = None
_WORKER_DOMAIN: np.ndarray | None = None
_WORKER_SPACING: tuple[float, float, float] | None = None
_WORKER_DURATION_DAYS: float | None = None
_WORKER_START_TIME_DAY: float | None = None
_WORKER_DT_DAYS: float | None = None
_WORKER_EVENTS: tuple[FractionResponseEvent, ...] | None = None
_WORKER_THRESHOLD: float | None = None
_WORKER_TEMPERATURE: float | None = None
_WORKER_VOLUME_WEIGHT: float | None = None


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _survival_payload(value: float | np.ndarray) -> object:
    if isinstance(value, np.ndarray):
        return {
            "kind": "field",
            "sha256": _array_digest(value),
        }
    return {
        "kind": "scalar",
        "value": float(value),
    }


def _cache_signature(
    *,
    initial_state: TreatmentMemoryState,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    start_time_day: float,
    events: tuple[FractionResponseEvent, ...],
    config: Stage8CalibrationConfig,
) -> str:
    payload = {
        "schema": "stage8-calibration-cache-v2",
        "field": _array_digest(initial_state.field),
        "modifier": _array_digest(initial_state.proliferation_modifier),
        "observed": _array_digest(np.asarray(observed_mask, dtype=np.uint8)),
        "domain": _array_digest(np.asarray(domain_mask, dtype=np.uint8)),
        "spacing": spacing,
        "duration_days": duration_days,
        "start_time_day": start_time_day,
        "dt_days": config.dt_days,
        "threshold": config.observation_threshold,
        "soft_temperature": config.soft_temperature,
        "volume_weight": config.volume_weight,
        "events": [
            {
                "day": event.day,
                "immediate": _survival_payload(event.immediate_survival),
                "proliferation": _survival_payload(
                    event.proliferation_survival
                ),
            }
            for event in events
        ],
    }
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _candidate_key(candidate: _Candidate) -> str:
    payload = (
        f"D={candidate.diffusion:.12g};"
        f"rho={candidate.proliferation:.12g}"
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _cache_path(
    cache_dir: Path | None,
    signature: str,
    candidate: _Candidate,
) -> Path | None:
    if cache_dir is None:
        return None
    return cache_dir / signature / f"{_candidate_key(candidate)}.json"


def _load_cached_result(
    path: Path | None,
    candidate: _Candidate,
) -> CalibrationResult | None:
    if path is None or not path.is_file():
        return None

    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return None
    if (
        raw.get("diffusion") != candidate.diffusion
        or raw.get("proliferation") != candidate.proliferation
    ):
        return None

    dice = raw.get("dice")
    volume_error = raw.get("volume_error")
    loss = raw.get("loss")
    if not all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in (dice, volume_error, loss)
    ):
        return None

    return CalibrationResult(
        diffusion=candidate.diffusion,
        proliferation=candidate.proliferation,
        dice=float(dice),
        volume_error=float(volume_error),
        loss=float(loss),
    )


def _save_cached_result(path: Path | None, result: CalibrationResult) -> None:
    if path is None:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "diffusion": result.diffusion,
                "proliferation": result.proliferation,
                "dice": result.dice,
                "volume_error": result.volume_error,
                "loss": result.loss,
            },
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _initialize_worker(
    initial_field: np.ndarray,
    initial_modifier: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    start_time_day: float,
    dt_days: float,
    events: tuple[FractionResponseEvent, ...],
    threshold: float,
    temperature: float,
    volume_weight: float,
) -> None:
    global _WORKER_INITIAL_FIELD
    global _WORKER_INITIAL_MODIFIER
    global _WORKER_OBSERVED_MASK
    global _WORKER_DOMAIN
    global _WORKER_SPACING
    global _WORKER_DURATION_DAYS
    global _WORKER_START_TIME_DAY
    global _WORKER_DT_DAYS
    global _WORKER_EVENTS
    global _WORKER_THRESHOLD
    global _WORKER_TEMPERATURE
    global _WORKER_VOLUME_WEIGHT

    _WORKER_INITIAL_FIELD = initial_field
    _WORKER_INITIAL_MODIFIER = initial_modifier
    _WORKER_OBSERVED_MASK = observed_mask
    _WORKER_DOMAIN = domain_mask
    _WORKER_SPACING = spacing
    _WORKER_DURATION_DAYS = duration_days
    _WORKER_START_TIME_DAY = start_time_day
    _WORKER_DT_DAYS = dt_days
    _WORKER_EVENTS = events
    _WORKER_THRESHOLD = threshold
    _WORKER_TEMPERATURE = temperature
    _WORKER_VOLUME_WEIGHT = volume_weight


def _run_candidate(candidate: _Candidate) -> CalibrationResult:
    required = (
        _WORKER_INITIAL_FIELD,
        _WORKER_INITIAL_MODIFIER,
        _WORKER_OBSERVED_MASK,
        _WORKER_DOMAIN,
        _WORKER_SPACING,
        _WORKER_DURATION_DAYS,
        _WORKER_START_TIME_DAY,
        _WORKER_DT_DAYS,
        _WORKER_EVENTS,
        _WORKER_THRESHOLD,
        _WORKER_TEMPERATURE,
        _WORKER_VOLUME_WEIGHT,
    )
    if any(value is None for value in required):
        raise RuntimeError("Stage 8 calibration worker is not initialized")

    initial_field = _WORKER_INITIAL_FIELD
    initial_modifier = _WORKER_INITIAL_MODIFIER
    observed_mask = _WORKER_OBSERVED_MASK
    domain = _WORKER_DOMAIN
    spacing = _WORKER_SPACING
    duration_days = _WORKER_DURATION_DAYS
    start_time_day = _WORKER_START_TIME_DAY
    dt_days = _WORKER_DT_DAYS
    events = _WORKER_EVENTS
    threshold = _WORKER_THRESHOLD
    temperature = _WORKER_TEMPERATURE
    volume_weight = _WORKER_VOLUME_WEIGHT

    assert initial_field is not None
    assert initial_modifier is not None
    assert observed_mask is not None
    assert domain is not None
    assert spacing is not None
    assert duration_days is not None
    assert start_time_day is not None
    assert dt_days is not None
    assert events is not None
    assert threshold is not None
    assert temperature is not None
    assert volume_weight is not None

    state = TreatmentMemoryState(
        field=initial_field.copy(),
        proliferation_modifier=initial_modifier.copy(),
    )
    simulated = simulate_with_treatment_memory(
        state,
        ReactionDiffusionParameters(
            diffusion=candidate.diffusion,
            proliferation=candidate.proliferation,
        ),
        spacing=spacing,
        duration_days=duration_days,
        dt=dt_days,
        start_time_day=start_time_day,
        fraction_events=events,
        domain_mask=domain,
    )
    membership = soft_threshold_membership(
        simulated.field,
        threshold=threshold,
        temperature=temperature,
        domain_mask=domain,
    )
    dice = soft_dice_score(membership, observed_mask)
    volume_error = soft_relative_volume_error(membership, observed_mask)
    loss = 1.0 - dice + volume_weight * volume_error

    return CalibrationResult(
        diffusion=candidate.diffusion,
        proliferation=candidate.proliferation,
        dice=dice,
        volume_error=volume_error,
        loss=loss,
    )


def _deduplicate(
    results: list[CalibrationResult],
) -> list[CalibrationResult]:
    by_key: dict[tuple[float, float], CalibrationResult] = {}
    for result in results:
        key = (
            round(float(result.diffusion), 12),
            round(float(result.proliferation), 12),
        )
        existing = by_key.get(key)
        if existing is None or result.loss < existing.loss:
            by_key[key] = result
    return sorted(by_key.values(), key=lambda item: item.loss)


def _evaluate_grid(
    context: _GridContext,
    *,
    diffusion_values: list[float],
    proliferation_values: list[float],
) -> list[CalibrationResult]:
    candidates = [
        _Candidate(
            diffusion=float(diffusion),
            proliferation=float(proliferation),
        )
        for diffusion in diffusion_values
        for proliferation in proliferation_values
    ]
    results: list[CalibrationResult] = []
    pending: list[_Candidate] = []

    for candidate in candidates:
        cached = _load_cached_result(
            _cache_path(
                context.cache_dir,
                context.signature,
                candidate,
            ),
            candidate,
        )
        if cached is None:
            pending.append(candidate)
        else:
            results.append(cached)

    if pending:
        initializer_args = (
            np.asarray(context.initial_state.field, dtype=np.float32),
            np.asarray(
                context.initial_state.proliferation_modifier,
                dtype=np.float32,
            ),
            np.asarray(context.observed_mask, dtype=bool),
            np.asarray(context.domain_mask, dtype=bool),
            context.spacing,
            context.duration_days,
            context.start_time_day,
            context.config.dt_days,
            context.events,
            context.config.observation_threshold,
            context.config.soft_temperature,
            context.config.volume_weight,
        )
        effective_workers = min(
            max(1, context.workers),
            len(pending),
        )

        if effective_workers == 1:
            _initialize_worker(*initializer_args)
            computed = [_run_candidate(candidate) for candidate in pending]
        else:
            with ProcessPoolExecutor(
                max_workers=effective_workers,
                initializer=_initialize_worker,
                initargs=initializer_args,
            ) as executor:
                computed = list(executor.map(_run_candidate, pending))

        for candidate, result in zip(pending, computed, strict=True):
            _save_cached_result(
                _cache_path(
                    context.cache_dir,
                    context.signature,
                    candidate,
                ),
                result,
            )
            results.append(result)

    return _deduplicate(results)


def calibrate_stage8_interval(
    *,
    initial_state: TreatmentMemoryState,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    fraction_events: tuple[FractionResponseEvent, ...],
    config: Stage8CalibrationConfig,
    start_time_day: float = 0.0,
    cache_dir: Path | None = None,
    workers: int = 1,
) -> Stage8CalibrationRun:
    if duration_days <= 0.0:
        raise ValueError("duration_days must be positive")
    if start_time_day < 0.0:
        raise ValueError("start_time_day must be non-negative")
    if workers < 1:
        raise ValueError("workers must be at least 1")

    observed = np.asarray(observed_mask, dtype=bool)
    domain = np.asarray(domain_mask, dtype=bool)
    if observed.shape != initial_state.field.shape:
        raise ValueError("observed_mask must match initial state")
    if domain.shape != initial_state.field.shape:
        raise ValueError("domain_mask must match initial state")

    signature = _cache_signature(
        initial_state=initial_state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=spacing,
        duration_days=duration_days,
        start_time_day=start_time_day,
        events=fraction_events,
        config=config,
    )
    context = _GridContext(
        initial_state=initial_state,
        observed_mask=observed,
        domain_mask=domain,
        spacing=spacing,
        duration_days=duration_days,
        start_time_day=start_time_day,
        events=fraction_events,
        config=config,
        signature=signature,
        cache_dir=cache_dir,
        workers=workers,
    )
    coarse = _evaluate_grid(
        context,
        diffusion_values=list(config.diffusion_values),
        proliferation_values=list(config.proliferation_values),
    )
    coarse_best = coarse[0]
    all_results = list(coarse)
    refined_results: list[CalibrationResult] = []
    diffusion_axis = sorted(
        set(float(value) for value in config.diffusion_values)
    )
    proliferation_axis = sorted(
        set(float(value) for value in config.proliferation_values)
    )

    for _ in range(config.refinement_rounds):
        current_best = _deduplicate(all_results)[0]
        refined_diffusion = build_refined_axis(
            diffusion_axis,
            current_best.diffusion,
            upper_boundary_expansion_factor=(
                config.upper_boundary_expansion_factor
            ),
        )
        refined_proliferation = build_refined_axis(
            proliferation_axis,
            current_best.proliferation,
            upper_boundary_expansion_factor=(
                config.upper_boundary_expansion_factor
            ),
        )
        round_results = _evaluate_grid(
            context,
            diffusion_values=refined_diffusion,
            proliferation_values=refined_proliferation,
        )
        refined_results.extend(round_results)
        all_results.extend(round_results)
        diffusion_axis = sorted({*diffusion_axis, *refined_diffusion})
        proliferation_axis = sorted(
            {*proliferation_axis, *refined_proliferation}
        )

    combined = _deduplicate(all_results)
    diagnostics = assess_calibration_diagnostics(
        best=combined[0],
        candidates=combined,
    )

    return Stage8CalibrationRun(
        best=combined[0],
        coarse_best=coarse_best,
        diagnostics=diagnostics,
        candidates=tuple(combined),
        coarse_candidates=tuple(coarse),
        refined_candidates=tuple(_deduplicate(refined_results)),
        cache_signature=signature,
    )
