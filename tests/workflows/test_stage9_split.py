from __future__ import annotations

from gbm_twin.workflows.stage9_selection import (
    _development_and_reserve_ids,
)


def test_stage9_preserves_original_untouched_holdout() -> None:
    manifest: dict[str, object] = {
        "patients": [
            {
                "patient_id": 1,
                "split": "development-exposed",
                "core_eligible": True,
                "exposed_development": True,
            },
            {
                "patient_id": 2,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 3,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 4,
                "split": "untouched-holdout",
                "core_eligible": True,
                "exposed_development": False,
            },
        ]
    }

    development, reserve, holdout = _development_and_reserve_ids(
        manifest,
        development_ids={1, 2},
    )

    assert development == (1, 2)
    assert reserve == (3,)
    assert holdout == (4,)
