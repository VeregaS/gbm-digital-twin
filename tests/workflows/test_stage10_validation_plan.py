from __future__ import annotations

import pytest

from gbm_twin.workflows.stage10_validation_plan import (
    select_stage10_reserve_patient_ids,
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
