from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

from gbm_twin.api.config import ApiSettings
from gbm_twin.workflows.anatomy_runtime import (
    prepare_patient_atlas_preview,
)
from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.twin_artifacts import (
    target_spacing,
)


def _patient_ids(
    payload: dict[str, object],
) -> tuple[int, ...]:
    raw = payload.get(
        "patients"
    )

    if not isinstance(
        raw,
        list,
    ):
        raise ValueError(
            "cohort evaluation patients must be a list"
        )

    result: list[int] = []

    for item in raw:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "cohort patient entry must be a mapping"
            )

        patient_id = item.get(
            "patient_id"
        )

        if type(patient_id) is not int:
            raise ValueError(
                "patient_id must be an integer"
            )

        result.append(
            cast(
                int,
                patient_id,
            )
        )

    return tuple(
        result
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Precompute automatic-QC t1 atlas previews "
            "for sealed twin patients."
        )
    )

    parser.add_argument(
        "--patient-id",
        type=int,
        action="append",
        default=None,
        help=(
            "Optional patient id. Repeat to prewarm "
            "a subset; omit to use the sealed cohort."
        ),
    )

    args = parser.parse_args()

    settings = (
        ApiSettings.from_environment()
    )

    if settings.atlas_root is None:
        parser.error(
            "Atlas analysis is disabled."
        )

    if (
        settings
        .cohort_evaluation_root
        is None
    ):
        parser.error(
            "Cohort evaluation root is not configured."
        )

    evaluation = (
        load_sealed_cohort_evaluation(
            settings
            .cohort_evaluation_root
        )
    )

    payload = evaluation.manifest

    cohort_ids = _patient_ids(
        payload
    )

    requested = (
        cohort_ids
        if args.patient_id is None
        else tuple(
            args.patient_id
        )
    )

    unknown = sorted(
        set(
            requested
        )
        - set(
            cohort_ids
        )
    )

    if unknown:
        parser.error(
            "Patients are not present in the sealed cohort: "
            + ", ".join(
                str(
                    value
                )
                for value in unknown
            )
        )

    spacing = target_spacing(
        payload
    )

    failures: list[
        tuple[
            int,
            str,
        ]
    ] = []

    for (
        index,
        patient_id,
    ) in enumerate(
        requested,
        start=1,
    ):
        print(
            f"[atlas] {index}/{len(requested)} "
            f"patient={patient_id}",
            flush=True,
        )

        try:
            selection = (
                prepare_patient_atlas_preview(
                    metadata_root=(
                        settings.metadata_root
                    ),
                    patients_root=(
                        settings.patients_root
                    ),
                    atlas_root=(
                        settings.atlas_root
                    ),
                    patient_id=patient_id,
                    timepoint_name="t1",
                    target_spacing=(
                        spacing
                    ),
                )
            )

        except Exception as exc:
            failures.append(
                (
                    patient_id,
                    str(
                        exc
                    ),
                )
            )

            print(
                f"[atlas]   failed: {exc}",
                flush=True,
            )

            continue

        print(
            "[atlas]   "
            + selection.mode
            + " · "
            + (
                selection
                .automatic_qc_status
                or "no-qc"
            ),
            flush=True,
        )

    print()
    print(
        "Atlas prewarm complete."
    )

    print(
        "Patients:",
        len(
            requested
        ),
    )

    print(
        "Failures:",
        len(
            failures
        ),
    )

    if failures:
        for (
            patient_id,
            message,
        ) in failures:
            print(
                f"  {patient_id}: {message}"
            )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
