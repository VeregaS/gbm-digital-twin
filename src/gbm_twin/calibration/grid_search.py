from concurrent.futures import (
    ProcessPoolExecutor,
)
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from gbm_twin.calibration.cache import (
    build_calibration_signature,
    candidate_cache_key,
    load_cached_metrics,
    save_cached_metrics,
)
from gbm_twin.evaluation.metrics import (
    dice_score,
    relative_volume_error,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.solver import (
    TreatmentModel,
    simulate_reaction_diffusion,
)


@dataclass(frozen=True)
class CalibrationResult:
    diffusion: float
    proliferation: float
    dice: float
    volume_error: float
    loss: float


@dataclass(frozen=True)
class CalibrationCandidate:
    diffusion: float
    proliferation: float
    cache_key: str | None


_WORKER_INITIAL_FIELD: np.ndarray | None = None
_WORKER_OBSERVED_MASK: np.ndarray | None = None
_WORKER_DOMAIN_MASK: np.ndarray | None = None
_WORKER_SPACING: tuple[
    float,
    float,
    float,
] | None = None
_WORKER_DURATION_DAYS: float | None = None
_WORKER_DT: float | None = None
_WORKER_THRESHOLD: float | None = None
_WORKER_TREATMENT: TreatmentModel | None = None
_WORKER_START_TIME_DAY: float | None = None


def _initialize_calibration_worker(
    initial_field: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    threshold: float,
    treatment: TreatmentModel | None,
    start_time_day: float,
) -> None:
    global _WORKER_INITIAL_FIELD
    global _WORKER_OBSERVED_MASK
    global _WORKER_DOMAIN_MASK
    global _WORKER_SPACING
    global _WORKER_DURATION_DAYS
    global _WORKER_DT
    global _WORKER_THRESHOLD
    global _WORKER_TREATMENT
    global _WORKER_START_TIME_DAY

    _WORKER_INITIAL_FIELD = initial_field
    _WORKER_OBSERVED_MASK = observed_mask
    _WORKER_DOMAIN_MASK = domain_mask
    _WORKER_SPACING = spacing
    _WORKER_DURATION_DAYS = duration_days
    _WORKER_DT = dt
    _WORKER_THRESHOLD = threshold
    _WORKER_TREATMENT = treatment
    _WORKER_START_TIME_DAY = start_time_day


def _run_candidate(
    candidate: CalibrationCandidate,
) -> tuple[
    CalibrationCandidate,
    float,
    float,
]:
    if _WORKER_INITIAL_FIELD is None:
        raise RuntimeError(
            "Calibration worker initial field "
            "is not initialized"
        )

    if _WORKER_OBSERVED_MASK is None:
        raise RuntimeError(
            "Calibration worker observed mask "
            "is not initialized"
        )

    if _WORKER_DOMAIN_MASK is None:
        raise RuntimeError(
            "Calibration worker domain mask "
            "is not initialized"
        )

    if _WORKER_SPACING is None:
        raise RuntimeError(
            "Calibration worker spacing "
            "is not initialized"
        )

    if _WORKER_DURATION_DAYS is None:
        raise RuntimeError(
            "Calibration worker duration "
            "is not initialized"
        )

    if _WORKER_DT is None:
        raise RuntimeError(
            "Calibration worker dt "
            "is not initialized"
        )

    if _WORKER_THRESHOLD is None:
        raise RuntimeError(
            "Calibration worker threshold "
            "is not initialized"
        )

    if _WORKER_START_TIME_DAY is None:
        raise RuntimeError(
            "Calibration worker start time "
            "is not initialized"
        )

    params = ReactionDiffusionParameters(
        diffusion=candidate.diffusion,
        proliferation=(
            candidate.proliferation
        ),
    )

    simulated = simulate_reaction_diffusion(
        _WORKER_INITIAL_FIELD,
        params,
        spacing=_WORKER_SPACING,
        duration_days=(
            _WORKER_DURATION_DAYS
        ),
        dt=_WORKER_DT,
        domain_mask=(
            _WORKER_DOMAIN_MASK
        ),
        treatment=(
            _WORKER_TREATMENT
        ),
        start_time_day=(
            _WORKER_START_TIME_DAY
        ),
    )

    predicted = (
        simulated
        >= _WORKER_THRESHOLD
    )

    dice = dice_score(
        predicted,
        _WORKER_OBSERVED_MASK,
    )

    volume_error = relative_volume_error(
        predicted,
        _WORKER_OBSERVED_MASK,
    )

    return (
        candidate,
        dice,
        volume_error,
    )


def _run_candidates_sequentially(
    candidates: list[
        CalibrationCandidate
    ],
    *,
    initial_field: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    threshold: float,
    treatment: TreatmentModel | None,
    start_time_day: float,
) -> list[
    tuple[
        CalibrationCandidate,
        float,
        float,
    ]
]:
    _initialize_calibration_worker(
        initial_field,
        observed_mask,
        domain_mask,
        spacing,
        duration_days,
        dt,
        threshold,
        treatment,
        start_time_day,
    )

    return [
        _run_candidate(
            candidate
        )
        for candidate in candidates
    ]


def _run_candidates_parallel(
    candidates: list[
        CalibrationCandidate
    ],
    *,
    initial_field: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    threshold: float,
    treatment: TreatmentModel | None,
    start_time_day: float,
    workers: int,
) -> list[
    tuple[
        CalibrationCandidate,
        float,
        float,
    ]
]:
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=(
            _initialize_calibration_worker
        ),
        initargs=(
            initial_field,
            observed_mask,
            domain_mask,
            spacing,
            duration_days,
            dt,
            threshold,
            treatment,
            start_time_day,
        ),
    ) as executor:
        return list(
            executor.map(
                _run_candidate,
                candidates,
            )
        )


def grid_search(
    initial_field: np.ndarray,
    observed_mask: np.ndarray,
    domain_mask: np.ndarray,
    *,
    spacing: tuple[float, float, float],
    duration_days: float,
    dt: float,
    diffusion_values: list[float],
    proliferation_values: list[float],
    threshold: float = 0.5,
    volume_weight: float = 0.5,
    treatment: TreatmentModel | None = None,
    start_time_day: float = 0.0,
    cache_dir: Path | None = None,
    workers: int = 1,
) -> list[CalibrationResult]:
    if initial_field.shape != observed_mask.shape:
        raise ValueError(
            "Initial field and observed mask "
            "must have the same shape"
        )

    if initial_field.shape != domain_mask.shape:
        raise ValueError(
            "Initial field and domain mask "
            "must have the same shape"
        )

    if duration_days < 0:
        raise ValueError(
            "duration_days must be non-negative"
        )

    if dt <= 0:
        raise ValueError(
            "dt must be positive"
        )

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            "threshold must be within [0, 1]"
        )

    if volume_weight < 0:
        raise ValueError(
            "volume_weight must be non-negative"
        )

    if not diffusion_values:
        raise ValueError(
            "diffusion_values must not be empty"
        )

    if not proliferation_values:
        raise ValueError(
            "proliferation_values must not be empty"
        )

    if start_time_day < 0:
        raise ValueError(
            "start_time_day must be non-negative"
        )

    if workers < 1:
        raise ValueError(
            "workers must be at least 1"
        )

    simulation_initial = np.asarray(
        initial_field,
        dtype=np.float32,
    )

    observed = np.asarray(
        observed_mask,
        dtype=bool,
    )

    domain = np.asarray(
        domain_mask,
        dtype=bool,
    )

    cache_signature = None

    if cache_dir is not None:
        cache_signature = (
            build_calibration_signature(
                initial_field=(
                    simulation_initial
                ),
                observed_mask=observed,
                domain_mask=domain,
                spacing=spacing,
                duration_days=(
                    duration_days
                ),
                dt=dt,
                threshold=threshold,
                treatment=treatment,
                start_time_day=(
                    start_time_day
                ),
            )
        )

    cached_results: list[
        CalibrationResult
    ] = []

    pending_candidates: list[
        CalibrationCandidate
    ] = []

    for diffusion in diffusion_values:
        for proliferation in (
            proliferation_values
        ):
            cache_key = None
            cached_metrics = None

            if (
                cache_dir is not None
                and cache_signature
                is not None
            ):
                cache_key = (
                    candidate_cache_key(
                        cache_signature,
                        diffusion=diffusion,
                        proliferation=(
                            proliferation
                        ),
                    )
                )

                cached_metrics = (
                    load_cached_metrics(
                        cache_dir,
                        cache_key,
                    )
                )

            if cached_metrics is None:
                pending_candidates.append(
                    CalibrationCandidate(
                        diffusion=diffusion,
                        proliferation=(
                            proliferation
                        ),
                        cache_key=cache_key,
                    )
                )

                continue

            dice, volume_error = (
                cached_metrics
            )

            loss = (
                1.0
                - dice
                + volume_weight
                * volume_error
            )

            print(
                f"Cache hit D={diffusion:.4f}, "
                f"rho={proliferation:.4f}"
            )

            print(
                f"  Dice={dice:.4f} "
                f"VolumeError="
                f"{volume_error:.2%} "
                f"Loss={loss:.4f}"
            )

            cached_results.append(
                CalibrationResult(
                    diffusion=diffusion,
                    proliferation=(
                        proliferation
                    ),
                    dice=dice,
                    volume_error=(
                        volume_error
                    ),
                    loss=loss,
                )
            )

    if pending_candidates:
        print()

        print(
            "PDE candidates to run: "
            f"{len(pending_candidates)}"
        )

        effective_workers = min(
            workers,
            len(pending_candidates),
        )

        print(
            f"Workers: {effective_workers}"
        )

        for candidate in (
            pending_candidates
        ):
            print(
                "  queued "
                f"D={candidate.diffusion:.4f}, "
                "rho="
                f"{candidate.proliferation:.4f}"
            )

        if effective_workers == 1:
            computed = (
                _run_candidates_sequentially(
                    pending_candidates,
                    initial_field=(
                        simulation_initial
                    ),
                    observed_mask=observed,
                    domain_mask=domain,
                    spacing=spacing,
                    duration_days=(
                        duration_days
                    ),
                    dt=dt,
                    threshold=threshold,
                    treatment=treatment,
                    start_time_day=(
                        start_time_day
                    ),
                )
            )

        else:
            computed = (
                _run_candidates_parallel(
                    pending_candidates,
                    initial_field=(
                        simulation_initial
                    ),
                    observed_mask=observed,
                    domain_mask=domain,
                    spacing=spacing,
                    duration_days=(
                        duration_days
                    ),
                    dt=dt,
                    threshold=threshold,
                    treatment=treatment,
                    start_time_day=(
                        start_time_day
                    ),
                    workers=(
                        effective_workers
                    ),
                )
            )

    else:
        computed = []

    computed_results: list[
        CalibrationResult
    ] = []

    for (
        candidate,
        dice,
        volume_error,
    ) in computed:
        loss = (
            1.0
            - dice
            + volume_weight
            * volume_error
        )

        print(
            f"Result "
            f"D={candidate.diffusion:.4f}, "
            f"rho={candidate.proliferation:.4f}"
        )

        print(
            f"  Dice={dice:.4f} "
            f"VolumeError="
            f"{volume_error:.2%} "
            f"Loss={loss:.4f}"
        )

        if (
            cache_dir is not None
            and candidate.cache_key
            is not None
        ):
            save_cached_metrics(
                cache_dir,
                candidate.cache_key,
                dice=dice,
                volume_error=(
                    volume_error
                ),
            )

        computed_results.append(
            CalibrationResult(
                diffusion=(
                    candidate.diffusion
                ),
                proliferation=(
                    candidate.proliferation
                ),
                dice=dice,
                volume_error=(
                    volume_error
                ),
                loss=loss,
            )
        )

    results = (
        cached_results
        + computed_results
    )

    results.sort(
        key=lambda result: result.loss
    )

    return results