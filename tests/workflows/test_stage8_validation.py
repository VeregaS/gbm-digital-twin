from __future__ import annotations

from gbm_twin.workflows.stage8_validation import _validation_patient_ids


def test_internal_validation_ids_exclude_exposed_and_holdout() -> None:
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
                "split": "internal-validation",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 4,
                "split": "untouched-holdout",
                "core_eligible": True,
                "exposed_development": False,
            },
            {
                "patient_id": 5,
                "split": "development",
                "core_eligible": False,
                "exposed_development": False,
            },
        ]
    }

    assert _validation_patient_ids(manifest) == (2, 3)
