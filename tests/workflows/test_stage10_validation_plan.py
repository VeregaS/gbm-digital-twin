from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from gbm_twin.workflows.stage10_validation_plan import (
    Stage10ValidationPlan,
    select_stage10_reserve_patient_ids,
    verify_stage10_validation_cohort,
)


def _audit(
) -> dict[str, object]:
    return {
        "patients": [
            {
                "patient_id": 10,
                "split": "development",
                "split_stratum": (
                    "t1gd-only:rt-conventional"
                ),
            },
            {
                "patient_id": 11,
                "split": "development",
                "split_stratum": (
                    "t1gd-only:rt-conventional"
                ),
            },
            {
                "patient_id": 20,
                "split": "development",
                "split_stratum": (
                    "mpmri:rt-conventional"
                ),
            },
            {
                "patient_id": 21,
                "split": "development",
                "split_stratum": (
                    "mpmri:rt-conventional"
                ),
            },
            {
                "patient_id": 99,
                "split": "untouched-holdout",
                "split_stratum": (
                    "mpmri:rt-conventional"
                ),
            },
        ]
    }


def test_stage10_reserve_selection_is_deterministic_and_stratified(
) -> None:
    first = (
        select_stage10_reserve_patient_ids(
            audit_manifest=_audit(),
            reserve_patient_ids=(
                10,
                11,
                20,
                21,
            ),
            untouched_holdout_patient_ids=(
                99,
            ),
            count=2,
            seed=2026,
        )
    )

    second = (
        select_stage10_reserve_patient_ids(
            audit_manifest=_audit(),
            reserve_patient_ids=(
                10,
                11,
                20,
                21,
            ),
            untouched_holdout_patient_ids=(
                99,
            ),
            count=2,
            seed=2026,
        )
    )

    assert first == second
    assert len(
        first
    ) == 2
    assert (
        len(
            set(
                first
            )
            & {
                10,
                11,
            }
        )
        == 1
    )
    assert (
        len(
            set(
                first
            )
            & {
                20,
                21,
            }
        )
        == 1
    )


@pytest.mark.parametrize("field", [
    "patient_ids", "seed", "remaining_reserve_patient_ids", "untouched_holdout_patient_ids",
])
def test_cohort_verifier_rejects_changes_even_with_reserve_membership(
    tmp_path: Path, field: str,
) -> None:
    reserve = (10, 11, 20, 21)
    kwargs = dict(
        audit_manifest=_audit(), reserve_patient_ids=reserve,
        untouched_holdout_patient_ids=(99,), count=2, seed=2026,
    )
    ids = select_stage10_reserve_patient_ids(**kwargs)
    remaining = tuple(sorted(set(reserve) - set(ids)))
    plan = Stage10ValidationPlan(
        directory=tmp_path, patient_ids=ids, remaining_reserve_patient_ids=remaining,
        untouched_holdout_patient_ids=(99,), seed=2026,
        stage10_selection_sha256="a", stage8_data_audit_sha256="b",
        frozen_model_config_sha256="c", validation_config_sha256="d",
    )
    verify_stage10_validation_cohort(plan, **kwargs)
    changes = dict(
        patient_ids=ids[:1], seed=2027, remaining_reserve_patient_ids=(),
        untouched_holdout_patient_ids=(),
    )
    tampered = replace(plan, **{field: changes[field]})
    with pytest.raises(ValueError, match="prespecified"):
        verify_stage10_validation_cohort(tampered, **kwargs)


def test_stage10_reserve_selection_rejects_holdout_contamination(
) -> None:
    with pytest.raises(
        ValueError,
        match="holdout",
    ):
        select_stage10_reserve_patient_ids(
            audit_manifest=_audit(),
            reserve_patient_ids=(
                10,
                99,
            ),
            untouched_holdout_patient_ids=(
                99,
            ),
            count=1,
            seed=2026,
        )
