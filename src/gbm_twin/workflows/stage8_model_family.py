from __future__ import annotations

from dataclasses import dataclass

from gbm_twin.workflows.stage8_protocol import Stage8ProtocolConfig


@dataclass(frozen=True)
class Stage8ModelCandidate:
    candidate_id: str
    use_spatial_rtdose: bool
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
    """Return a nested family ordered from simpler to richer models.

    FLAIR/low-density observation is deliberately not enabled automatically:
    availability of a raw FLAIR image is not equivalent to a validated
    infiltrative-tumor segmentation. A future candidate may set
    ``use_infiltrative_observation=True`` only when such a mask has explicit
    provenance.
    """

    candidates: list[Stage8ModelCandidate] = []

    for spatial in (False, True):
        for survival in protocol.treatment_memory.proliferation_survival_candidates:
            suffix = "spatial" if spatial else "uniform"
            memory = (
                "no-memory"
                if survival == 1.0
                else f"prolif-sf-{survival:.6g}"
            )
            candidates.append(
                Stage8ModelCandidate(
                    candidate_id=f"stage8-{suffix}-{memory}",
                    use_spatial_rtdose=spatial,
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
                -candidate.proliferation_survival,
                candidate.candidate_id,
            ),
        )
    )
