from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import fmean, median


@dataclass(frozen=True)
class Stage8PatientCandidateScore:
    patient_id: int
    candidate_id: str
    complexity_rank: int
    dice: float
    relative_volume_error: float
    hd95_mm: float | None = None
    centroid_distance_mm: float | None = None

    def __post_init__(self) -> None:
        if self.patient_id < 0:
            raise ValueError("patient_id must be non-negative")

        if not self.candidate_id:
            raise ValueError("candidate_id cannot be empty")

        if self.complexity_rank < 0:
            raise ValueError("complexity_rank must be non-negative")

        if not 0.0 <= self.dice <= 1.0:
            raise ValueError("dice must be within [0, 1]")

        if self.relative_volume_error < 0.0:
            raise ValueError("relative_volume_error must be non-negative")


@dataclass(frozen=True)
class Stage8CandidateSummary:
    candidate_id: str
    complexity_rank: int
    patient_count: int
    mean_dice: float
    median_dice: float
    mean_relative_volume_error: float
    median_relative_volume_error: float


@dataclass(frozen=True)
class Stage8LOOFold:
    held_out_patient_id: int
    selected_candidate_id: str
    held_out_dice: float
    held_out_relative_volume_error: float


@dataclass(frozen=True)
class Stage8ModelSelectionResult:
    development_patient_ids: tuple[int, ...]
    candidate_summaries: tuple[Stage8CandidateSummary, ...]
    selected_candidate_id: str
    loo_folds: tuple[Stage8LOOFold, ...]
    loo_mean_dice: float
    loo_median_dice: float
    loo_mean_relative_volume_error: float
    loo_selection_counts: dict[str, int]


def _score_index(
    scores: tuple[Stage8PatientCandidateScore, ...],
) -> dict[tuple[str, int], Stage8PatientCandidateScore]:
    result: dict[
        tuple[str, int],
        Stage8PatientCandidateScore,
    ] = {}

    for score in scores:
        key = (score.candidate_id, score.patient_id)

        if key in result:
            raise ValueError(
                "Duplicate Stage 8 candidate/patient score: "
                f"{score.candidate_id}, {score.patient_id}"
            )

        result[key] = score

    return result


def _candidate_summaries(
    scores: tuple[Stage8PatientCandidateScore, ...],
    patient_ids: tuple[int, ...],
) -> tuple[Stage8CandidateSummary, ...]:
    requested = set(patient_ids)
    candidate_ids = sorted({score.candidate_id for score in scores})
    summaries: list[Stage8CandidateSummary] = []

    for candidate_id in candidate_ids:
        candidate_scores = [
            score
            for score in scores
            if score.candidate_id == candidate_id
            and score.patient_id in requested
        ]
        covered = {score.patient_id for score in candidate_scores}

        # Compare model families on a paired cohort only. A richer model that
        # is unavailable for one development patient cannot win by evaluating
        # itself on an easier subset.
        if covered != requested:
            continue

        ranks = {score.complexity_rank for score in candidate_scores}

        if len(ranks) != 1:
            raise ValueError(
                f"Candidate {candidate_id} has inconsistent complexity ranks"
            )

        dice_values = [score.dice for score in candidate_scores]
        volume_errors = [
            score.relative_volume_error
            for score in candidate_scores
        ]
        summaries.append(
            Stage8CandidateSummary(
                candidate_id=candidate_id,
                complexity_rank=ranks.pop(),
                patient_count=len(candidate_scores),
                mean_dice=float(fmean(dice_values)),
                median_dice=float(median(dice_values)),
                mean_relative_volume_error=float(
                    fmean(volume_errors)
                ),
                median_relative_volume_error=float(
                    median(volume_errors)
                ),
            )
        )

    return tuple(
        sorted(
            summaries,
            key=lambda summary: (
                -summary.mean_dice,
                -summary.median_dice,
                summary.mean_relative_volume_error,
                summary.complexity_rank,
                summary.candidate_id,
            ),
        )
    )


def _best_candidate(
    scores: tuple[Stage8PatientCandidateScore, ...],
    patient_ids: tuple[int, ...],
) -> Stage8CandidateSummary:
    summaries = _candidate_summaries(scores, patient_ids)

    if not summaries:
        raise ValueError(
            "No Stage 8 candidate covers the complete paired development cohort"
        )

    return summaries[0]


def select_stage8_model(
    scores: tuple[Stage8PatientCandidateScore, ...],
    *,
    development_patient_ids: tuple[int, ...],
) -> Stage8ModelSelectionResult:
    patient_ids = tuple(sorted(set(development_patient_ids)))

    if len(patient_ids) < 3:
        raise ValueError(
            "Stage 8 leave-one-patient-out selection requires at least 3 patients"
        )

    index = _score_index(scores)
    summaries = _candidate_summaries(scores, patient_ids)

    if not summaries:
        raise ValueError("No complete Stage 8 candidate matrix")

    # Candidate eligibility is fixed on the complete paired development
    # cohort before any LOO fold is formed. Otherwise a candidate missing the
    # held-out patient's score could look artificially strong on the smaller
    # training fold and then be impossible to evaluate on that held-out case.
    eligible_candidate_ids = {
        summary.candidate_id
        for summary in summaries
    }
    paired_scores = tuple(
        score
        for score in scores
        if score.candidate_id in eligible_candidate_ids
    )

    final_selected = summaries[0]
    folds: list[Stage8LOOFold] = []

    for held_out in patient_ids:
        training_ids = tuple(
            patient_id
            for patient_id in patient_ids
            if patient_id != held_out
        )
        selected = _best_candidate(paired_scores, training_ids)
        held_out_score = index.get((selected.candidate_id, held_out))

        if held_out_score is None:
            raise RuntimeError(
                "Globally paired Stage 8 candidate is missing a held-out score"
            )

        folds.append(
            Stage8LOOFold(
                held_out_patient_id=held_out,
                selected_candidate_id=selected.candidate_id,
                held_out_dice=held_out_score.dice,
                held_out_relative_volume_error=(
                    held_out_score.relative_volume_error
                ),
            )
        )

    loo_dice = [fold.held_out_dice for fold in folds]
    loo_volume = [
        fold.held_out_relative_volume_error
        for fold in folds
    ]

    return Stage8ModelSelectionResult(
        development_patient_ids=patient_ids,
        candidate_summaries=summaries,
        selected_candidate_id=final_selected.candidate_id,
        loo_folds=tuple(folds),
        loo_mean_dice=float(fmean(loo_dice)),
        loo_median_dice=float(median(loo_dice)),
        loo_mean_relative_volume_error=float(fmean(loo_volume)),
        loo_selection_counts=dict(
            sorted(
                Counter(
                    fold.selected_candidate_id
                    for fold in folds
                ).items()
            )
        ),
    )
