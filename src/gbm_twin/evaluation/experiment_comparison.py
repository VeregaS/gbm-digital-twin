from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean, median
from typing import cast


@dataclass(frozen=True)
class PatientAccuracyDelta:
    patient_id: int
    baseline_twin_dice: float
    candidate_twin_dice: float
    twin_dice_delta: float

    baseline_delta_vs_persistence: float
    candidate_delta_vs_persistence: float
    delta_vs_persistence_change: float

    baseline_calibration_dice: float
    candidate_calibration_dice: float
    calibration_dice_delta: float

    baseline_diffusion: float
    candidate_diffusion: float
    baseline_proliferation: float
    candidate_proliferation: float

    baseline_calibration_identifiable: bool
    candidate_calibration_identifiable: bool

    baseline_diffusion_at_boundary: bool
    candidate_diffusion_at_boundary: bool
    baseline_proliferation_at_boundary: bool
    candidate_proliferation_at_boundary: bool


@dataclass(frozen=True)
class AccuracyExperimentComparison:
    patient_count: int

    mean_twin_dice_delta: float
    median_twin_dice_delta: float

    improved_patient_count: int
    equal_patient_count: int
    degraded_patient_count: int

    mean_delta_vs_persistence_change: float

    baseline_boundary_patient_count: int
    candidate_boundary_patient_count: int

    baseline_non_identifiable_count: int
    candidate_non_identifiable_count: int

    patients: tuple[
        PatientAccuracyDelta,
        ...,
    ]


def _require_mapping(
    value: object,
    *,
    name: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _require_list(
    value: object,
    *,
    name: str,
) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(
            f"{name} must be a list"
        )

    return cast(
        list[object],
        value,
    )


def _require_int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(key)

    if type(value) is not int:
        raise ValueError(
            f"Field {key!r} must be an integer"
        )

    return cast(
        int,
        value,
    )


def _require_float(
    mapping: dict[str, object],
    key: str,
) -> float:
    value = mapping.get(key)

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise ValueError(
            f"Field {key!r} must be numeric"
        )

    return float(value)


def _require_bool(
    mapping: dict[str, object],
    key: str,
) -> bool:
    value = mapping.get(key)

    if type(value) is not bool:
        raise ValueError(
            f"Field {key!r} must be boolean"
        )

    return cast(
        bool,
        value,
    )


def _patient_rows(
    payload: dict[str, object],
) -> dict[int, dict[str, object]]:
    raw_rows = _require_list(
        payload.get("patients"),
        name="patients",
    )

    rows: dict[
        int,
        dict[str, object],
    ] = {}

    for index, raw_row in enumerate(
        raw_rows
    ):
        row = _require_mapping(
            raw_row,
            name=f"patients[{index}]",
        )

        patient_id = _require_int(
            row,
            "patient_id",
        )

        if patient_id in rows:
            raise ValueError(
                "Duplicate patient_id in analysis payload: "
                f"{patient_id}"
            )

        rows[patient_id] = row

    return rows


def _at_any_boundary(
    row: dict[str, object],
) -> bool:
    return (
        _require_bool(
            row,
            "diffusion_at_boundary",
        )
        or _require_bool(
            row,
            "proliferation_at_boundary",
        )
    )


def compare_cohort_analyses(
    baseline: dict[str, object],
    candidate: dict[str, object],
    *,
    equality_tolerance: float = 1e-12,
) -> AccuracyExperimentComparison:
    if equality_tolerance < 0.0:
        raise ValueError(
            "equality_tolerance must be non-negative"
        )

    baseline_rows = _patient_rows(
        baseline
    )
    candidate_rows = _patient_rows(
        candidate
    )

    if baseline_rows.keys() != candidate_rows.keys():
        missing = sorted(
            baseline_rows.keys()
            - candidate_rows.keys()
        )
        added = sorted(
            candidate_rows.keys()
            - baseline_rows.keys()
        )

        raise ValueError(
            "Cohort analyses contain different patients; "
            f"missing={missing}, added={added}"
        )

    patient_deltas: list[
        PatientAccuracyDelta
    ] = []

    for patient_id in sorted(
        baseline_rows
    ):
        baseline_row = baseline_rows[
            patient_id
        ]
        candidate_row = candidate_rows[
            patient_id
        ]

        baseline_twin_dice = _require_float(
            baseline_row,
            "twin_dice",
        )
        candidate_twin_dice = _require_float(
            candidate_row,
            "twin_dice",
        )

        baseline_persistence_delta = _require_float(
            baseline_row,
            "twin_minus_persistence_dice",
        )
        candidate_persistence_delta = _require_float(
            candidate_row,
            "twin_minus_persistence_dice",
        )

        baseline_calibration_dice = _require_float(
            baseline_row,
            "calibration_dice",
        )
        candidate_calibration_dice = _require_float(
            candidate_row,
            "calibration_dice",
        )

        patient_deltas.append(
            PatientAccuracyDelta(
                patient_id=patient_id,
                baseline_twin_dice=(
                    baseline_twin_dice
                ),
                candidate_twin_dice=(
                    candidate_twin_dice
                ),
                twin_dice_delta=(
                    candidate_twin_dice
                    - baseline_twin_dice
                ),
                baseline_delta_vs_persistence=(
                    baseline_persistence_delta
                ),
                candidate_delta_vs_persistence=(
                    candidate_persistence_delta
                ),
                delta_vs_persistence_change=(
                    candidate_persistence_delta
                    - baseline_persistence_delta
                ),
                baseline_calibration_dice=(
                    baseline_calibration_dice
                ),
                candidate_calibration_dice=(
                    candidate_calibration_dice
                ),
                calibration_dice_delta=(
                    candidate_calibration_dice
                    - baseline_calibration_dice
                ),
                baseline_diffusion=_require_float(
                    baseline_row,
                    "diffusion",
                ),
                candidate_diffusion=_require_float(
                    candidate_row,
                    "diffusion",
                ),
                baseline_proliferation=_require_float(
                    baseline_row,
                    "proliferation",
                ),
                candidate_proliferation=_require_float(
                    candidate_row,
                    "proliferation",
                ),
                baseline_calibration_identifiable=(
                    _require_bool(
                        baseline_row,
                        "calibration_identifiable",
                    )
                ),
                candidate_calibration_identifiable=(
                    _require_bool(
                        candidate_row,
                        "calibration_identifiable",
                    )
                ),
                baseline_diffusion_at_boundary=(
                    _require_bool(
                        baseline_row,
                        "diffusion_at_boundary",
                    )
                ),
                candidate_diffusion_at_boundary=(
                    _require_bool(
                        candidate_row,
                        "diffusion_at_boundary",
                    )
                ),
                baseline_proliferation_at_boundary=(
                    _require_bool(
                        baseline_row,
                        "proliferation_at_boundary",
                    )
                ),
                candidate_proliferation_at_boundary=(
                    _require_bool(
                        candidate_row,
                        "proliferation_at_boundary",
                    )
                ),
            )
        )

    if not patient_deltas:
        raise ValueError(
            "Cannot compare empty cohort analyses"
        )

    dice_deltas = [
        row.twin_dice_delta
        for row in patient_deltas
    ]

    persistence_changes = [
        row.delta_vs_persistence_change
        for row in patient_deltas
    ]

    improved = sum(
        delta > equality_tolerance
        for delta in dice_deltas
    )
    degraded = sum(
        delta < -equality_tolerance
        for delta in dice_deltas
    )
    equal = (
        len(dice_deltas)
        - improved
        - degraded
    )

    baseline_boundary_count = sum(
        _at_any_boundary(
            baseline_rows[patient_id]
        )
        for patient_id in baseline_rows
    )

    candidate_boundary_count = sum(
        _at_any_boundary(
            candidate_rows[patient_id]
        )
        for patient_id in candidate_rows
    )

    baseline_non_identifiable = sum(
        not _require_bool(
            row,
            "calibration_identifiable",
        )
        for row in baseline_rows.values()
    )

    candidate_non_identifiable = sum(
        not _require_bool(
            row,
            "calibration_identifiable",
        )
        for row in candidate_rows.values()
    )

    return AccuracyExperimentComparison(
        patient_count=len(
            patient_deltas
        ),
        mean_twin_dice_delta=float(
            fmean(dice_deltas)
        ),
        median_twin_dice_delta=float(
            median(dice_deltas)
        ),
        improved_patient_count=improved,
        equal_patient_count=equal,
        degraded_patient_count=degraded,
        mean_delta_vs_persistence_change=float(
            fmean(
                persistence_changes
            )
        ),
        baseline_boundary_patient_count=(
            baseline_boundary_count
        ),
        candidate_boundary_patient_count=(
            candidate_boundary_count
        ),
        baseline_non_identifiable_count=(
            baseline_non_identifiable
        ),
        candidate_non_identifiable_count=(
            candidate_non_identifiable
        ),
        patients=tuple(
            patient_deltas
        ),
    )
