from __future__ import annotations

import math
from dataclasses import dataclass

from gbm_twin.workflows.stage8_protocol import Stage8ProtocolConfig


@dataclass(frozen=True)
class Stage8ModelCandidate:
    candidate_id: str
    use_spatial_rtdose: bool
    effective_alpha_per_gy: float
    alpha_beta_ratio_gy: float
    proliferation_survival: float
    use_infiltrative_observation: bool = False

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id cannot be empty")

        if not math.isfinite(self.effective_alpha_per_gy) or self.effective_alpha_per_gy <= 0.0:
            raise ValueError("effective_alpha_per_gy must be finite and positive")

        if not math.isfinite(self.alpha_beta_ratio_gy) or self.alpha_beta_ratio_gy <= 0.0:
            raise ValueError("alpha_beta_ratio_gy must be finite and positive")

        if (
            not math.isfinite(self.proliferation_survival)
            or not 0.0 < self.proliferation_survival <= 1.0
        ):
            raise ValueError(
                "proliferation_survival must be finite and within (0, 1]"
            )

    @property
    def has_treatment_memory(self) -> bool:
        return self.proliferation_survival < 1.0

    @property
    def complexity_rank(self) -> int:
        return (
            int(self.use_spatial_rtdose)
            + int(self.has_treatment_memory)
            + int(self.use_infiltrative_observation)
        )


def _candidate_id(
    *,
    spatial: bool,
    alpha: float,
    proliferation_survival: float,
) -> str:
    dose = "spatial" if spatial else "uniform"
    memory = (
        "no-memory"
        if proliferation_survival == 1.0
        else f"prolif-sf-{proliferation_survival:.6g}"
    )
    return f"stage8-{dose}-alpha-{alpha:.6g}-{memory}"


def _candidate(
    protocol: Stage8ProtocolConfig,
    *,
    spatial: bool,
    alpha: float,
    proliferation_survival: float,
) -> Stage8ModelCandidate:
    return Stage8ModelCandidate(
        candidate_id=_candidate_id(
            spatial=spatial,
            alpha=alpha,
            proliferation_survival=proliferation_survival,
        ),
        use_spatial_rtdose=spatial,
        effective_alpha_per_gy=alpha,
        alpha_beta_ratio_gy=protocol.radiobiology.alpha_beta_ratio_gy,
        proliferation_survival=proliferation_survival,
    )


def _unique(
    candidates: list[Stage8ModelCandidate],
) -> tuple[Stage8ModelCandidate, ...]:
    by_id = {candidate.candidate_id: candidate for candidate in candidates}

    if len(by_id) != len(candidates):
        raise ValueError("Stage 8 model-family construction produced duplicate IDs")

    return tuple(by_id.values())


def build_radiobiology_candidates(
    protocol: Stage8ProtocolConfig,
) -> tuple[Stage8ModelCandidate, ...]:
    """Phase 1: isolate the cohort-level effective alpha assumption.

    Dose is uniform and treatment memory is disabled so alpha is not selected
    while simultaneously changing two other mechanisms.
    """

    return _unique(
        [
            _candidate(
                protocol,
                spatial=False,
                alpha=alpha,
                proliferation_survival=1.0,
            )
            for alpha in protocol.radiobiology.effective_alpha_candidates_per_gy
        ]
    )


def build_dose_candidates(
    protocol: Stage8ProtocolConfig,
    *,
    effective_alpha_per_gy: float,
) -> tuple[Stage8ModelCandidate, ...]:
    """Phase 2: compare uniform and spatial dose at fixed alpha."""

    return _unique(
        [
            _candidate(
                protocol,
                spatial=spatial,
                alpha=effective_alpha_per_gy,
                proliferation_survival=1.0,
            )
            for spatial in (False, True)
        ]
    )


def build_memory_candidates(
    protocol: Stage8ProtocolConfig,
    *,
    effective_alpha_per_gy: float,
    use_spatial_rtdose: bool,
) -> tuple[Stage8ModelCandidate, ...]:
    """Phase 3: compare persistent proliferation response at fixed RT model."""

    survivals = (
        protocol.treatment_memory.proliferation_survival_candidates
        if protocol.treatment_memory.enabled
        else (1.0,)
    )

    return _unique(
        [
            _candidate(
                protocol,
                spatial=use_spatial_rtdose,
                alpha=effective_alpha_per_gy,
                proliferation_survival=survival,
            )
            for survival in survivals
        ]
    )


def build_final_alpha_sensitivity_candidates(
    protocol: Stage8ProtocolConfig,
    *,
    use_spatial_rtdose: bool,
    proliferation_survival: float,
) -> tuple[Stage8ModelCandidate, ...]:
    """Phase 4: re-check alpha after the treatment structure is fixed.

    This bounded sensitivity pass captures the main alpha/structure interaction
    without returning to a full 4 x 2 x N Cartesian search.
    """

    return _unique(
        [
            _candidate(
                protocol,
                spatial=use_spatial_rtdose,
                alpha=alpha,
                proliferation_survival=proliferation_survival,
            )
            for alpha in protocol.radiobiology.effective_alpha_candidates_per_gy
        ]
    )


def build_stage8_model_family(
    protocol: Stage8ProtocolConfig,
) -> tuple[Stage8ModelCandidate, ...]:
    """Return the Phase-1 family for compatibility with older callers.

    Stage 8 model selection itself is sequential and must use the dedicated
    phase builders above. Keeping this function avoids breaking exploratory
    imports while preventing accidental 32-way Cartesian production searches.
    """

    return build_radiobiology_candidates(protocol)
