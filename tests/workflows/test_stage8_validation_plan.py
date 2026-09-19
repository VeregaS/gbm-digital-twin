from __future__ import annotations

from gbm_twin.workflows.stage8_validation_plan import (
    select_validation_patient_ids,
)


def _manifest() -> dict[str, object]:
    return {
        "patients": [
            {
                "patient_id": 1,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
                "split_stratum": "t1gd-only:rt-conventional",
            },
            {
                "patient_id": 2,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
                "split_stratum": "t1gd-only:rt-conventional",
            },
            {
                "patient_id": 3,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
                "split_stratum": "mpmri:rt-conventional",
            },
            {
                "patient_id": 4,
                "split": "development",
                "core_eligible": True,
                "exposed_development": False,
                "split_stratum": "mpmri:rt-conventional",
            },
            {
                "patient_id": 5,
                "split": "untouched-holdout",
                "core_eligible": True,
                "exposed_development": False,
                "split_stratum": "mpmri:rt-conventional",
            },
            {
                "patient_id": 6,
                "split": "development-exposed",
                "core_eligible": True,
                "exposed_development": True,
                "split_stratum": "t1gd-only:rt-conventional",
            },
        ]
    }


def test_compact_validation_selection_is_deterministic_and_stratified() -> None:
    first = select_validation_patient_ids(
        _manifest(),
        count=2,
        seed=17,
    )
    second = select_validation_patient_ids(
        _manifest(),
        count=2,
        seed=17,
    )

    assert first == second
    assert len(first) == 2
    assert 5 not in first
    assert 6 not in first

    groups = {
        1: "t1gd",
        2: "t1gd",
        3: "mpmri",
        4: "mpmri",
    }
    assert {groups[patient_id] for patient_id in first} == {
        "t1gd",
        "mpmri",
    }


def test_compact_validation_selection_rejects_oversized_request() -> None:
    try:
        select_validation_patient_ids(
            _manifest(),
            count=5,
            seed=17,
        )
    except ValueError as exc:
        assert "exceeds" in str(exc)
    else:
        raise AssertionError("Expected oversized validation request to fail")
