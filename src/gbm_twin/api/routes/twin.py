from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from gbm_twin.api.config import (
    ApiSettings,
    get_api_settings,
)
from gbm_twin.api.schemas.twin import (
    TwinCohortResponse,
    TwinPatientEvaluationResponse,
    TwinPatientListItemResponse,
    TwinPatientListResponse,
)
from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationResult,
    PatientEvaluationPayload,
)
from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
    summarize_cohort_evaluation,
)

router = APIRouter(
    prefix="/twin",
    tags=["twin"],
)

SettingsDependency = Annotated[
    ApiSettings,
    Depends(get_api_settings),
]


def _load_evaluation(
    settings: ApiSettings,
) -> CohortEvaluationResult:
    root = (
        settings
        .cohort_evaluation_root
    )

    if root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cohort evaluation root "
                "is not configured"
            ),
        )

    try:
        return (
            load_sealed_cohort_evaluation(
                root
            )
        )
    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


def _find_patient(
    evaluation: CohortEvaluationResult,
    patient_id: int,
) -> PatientEvaluationPayload:
    for patient in (
        evaluation
        .manifest["patients"]
    ):
        if (
            patient["patient_id"]
            == patient_id
        ):
            return patient

    raise HTTPException(
        status_code=404,
        detail=(
            f"Patient {patient_id} "
            "is not present in the "
            "sealed V2 evaluation"
        ),
    )


@router.get(
    "/cohort",
    response_model=TwinCohortResponse,
)
def get_twin_cohort(
    settings: SettingsDependency,
) -> TwinCohortResponse:
    evaluation = (
        _load_evaluation(
            settings
        )
    )

    summary = (
        summarize_cohort_evaluation(
            evaluation.manifest
        )
    )

    return (
        TwinCohortResponse
        .from_payload(
            evaluation.manifest,
            summary,
        )
    )


@router.get(
    "/patients",
    response_model=(
        TwinPatientListResponse
    ),
)
def list_twin_patients(
    settings: SettingsDependency,
) -> TwinPatientListResponse:
    evaluation = (
        _load_evaluation(
            settings
        )
    )

    return TwinPatientListResponse(
        patients=[
            TwinPatientListItemResponse(
                patient_id=(
                    patient[
                        "patient_id"
                    ]
                ),
                target_timepoint=(
                    patient[
                        "target_timepoint"
                    ]
                ),
                target_day=(
                    patient[
                        "target_day"
                    ]
                ),
            )
            for patient
            in evaluation.manifest[
                "patients"
            ]
        ]
    )


@router.get(
    "/patients/{patient_id}",
    response_model=(
        TwinPatientEvaluationResponse
    ),
)
def get_twin_patient(
    patient_id: int,
    settings: SettingsDependency,
) -> TwinPatientEvaluationResponse:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    evaluation = (
        _load_evaluation(
            settings
        )
    )

    patient = _find_patient(
        evaluation,
        patient_id,
    )

    return (
        TwinPatientEvaluationResponse
        .from_payload(
            patient
        )
    )