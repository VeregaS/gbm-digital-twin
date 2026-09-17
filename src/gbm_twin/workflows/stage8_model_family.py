from __future__ import annotations

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


def build_stage8_model_family(
    protocol: Stage8ProtocolConfig,
) -> tuple[Stage8ModelCandidate, ...]:
    """Return a nested family ordered from simpler to richer mechanisms.

    Effective alpha and treatment-memory strength are cohort-level candidate
    hyperparameters. They are not jointly estimated as patient-specific values
    from a single treated interval. FLAIR/low-density observation is also not
    enabled automatically: raw FLAIR availability is not a validated
    infiltrative-tumor segmentation.
    """

    candidates: list[Stage8ModelCandidate] = []

    for spatial in (False, True):
        for alpha in protocol.radiobiology.effective_alpha_candidates_per_gy:
            for survival in (
                protocol.treatment_memory.proliferation_survival_candidates
            ):
                dose = "spatial" if spatial else "uniform"
                memory = (
                    "no-memory"
                    if survival == 1.0
                    else f"prolif-sf-{survival:.6g}"
                )
                candidate_id = (
                    f"stage8-{dose}-alpha-{alpha:.6g}-{memory}"
                )
                candidates.append(
                    Stage8ModelCandidate(
                        candidate_id=candidate_id,
                        use_spatial_rtdose=spatial,
                        effective_alpha_per_gy=alpha,
                        alpha_beta_ratio_gy=(
                            protocol.radiobiology.alpha_beta_ratio_gy
                        ),
                        proliferation_survival=survival,
                    )
                )

    unique = {candidate.candidate_id: candidate for candidate in candidates}

    return tuple(
        sorted(
            unique.values(),
            key=lambda candidate: (
                candidate.complexity_rank,
                candidate.use_spatial_rtdose,
                candidate.effective_alpha_per_gy,
                -candidate.proliferation_survival,
                candidate.candidate_id,
            ),
        )
    )
