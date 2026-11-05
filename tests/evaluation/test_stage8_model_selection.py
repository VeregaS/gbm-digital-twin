from __future__ import annotations

import pytest

from gbm_twin.evaluation.stage8_model_selection import (
    Stage8PatientCandidateScore,
    select_stage8_model,
)


def _score(
    patient_id: int,
    candidate_id: str,
    dice: float,
    volume_error: float,
    *,
    complexity: int,
) -> Stage8PatientCandidateScore:
    return Stage8PatientCandidateScore(
        patient_id=patient_id,
        candidate_id=candidate_id,
        complexity_rank=complexity,
        dice=dice,
        relative_volume_error=volume_error,
    )


def test_stage8_model_selection_is_paired_and_reports_loo() -> None:
    scores = (
        _score(1, "simple", 0.70, 0.20, complexity=0),
        _score(2, "simple", 0.70, 0.20, complexity=0),
        _score(3, "simple", 0.70, 0.20, complexity=0),
        _score(1, "rich", 0.80, 0.15, complexity=2),
        _score(2, "rich", 0.75, 0.15, complexity=2),
        _score(3, "rich", 0.72, 0.15, complexity=2),
    )

    result = select_stage8_model(
        scores,
        development_patient_ids=(1, 2, 3),
    )

    assert result.selected_candidate_id == "rich"
    assert result.candidate_summaries[0].candidate_id == "rich"
    assert len(result.loo_folds) == 3
    assert result.loo_mean_dice > 0.70


def test_incomplete_candidate_cannot_win_on_easier_subset() -> None:
    scores = (
        _score(1, "complete", 0.60, 0.20, complexity=0),
        _score(2, "complete", 0.60, 0.20, complexity=0),
        _score(3, "complete", 0.60, 0.20, complexity=0),
        _score(1, "incomplete", 0.99, 0.01, complexity=1),
        _score(2, "incomplete", 0.99, 0.01, complexity=1),
    )

    result = select_stage8_model(
        scores,
        development_patient_ids=(1, 2, 3),
    )

    assert result.selected_candidate_id == "complete"


def test_stage8_selection_requires_three_patients() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        select_stage8_model(
            (
                _score(1, "a", 0.5, 0.2, complexity=0),
                _score(2, "a", 0.5, 0.2, complexity=0),
            ),
            development_patient_ids=(1, 2),
        )
