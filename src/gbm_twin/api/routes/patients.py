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
from gbm_twin.api.schemas.patients import (
    PatientListItemResponse,
    PatientListResponse,
    PatientSummaryResponse,
)
from gbm_twin.workflows.patient_catalog import (
    discover_patient_ids,
    get_patient_catalog_summary,
)

router = APIRouter(
    prefix="/patients",
    tags=["patients"],
)

SettingsDependency = Annotated[
    ApiSettings,
    Depends(get_api_settings),
]


@router.get(
    "",
    response_model=PatientListResponse,
)
def list_patients(
    settings: SettingsDependency,
) -> PatientListResponse:
    try:
        patient_ids = discover_patient_ids(
            settings.patients_root
        )
    except (
        FileNotFoundError,
        NotADirectoryError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    return PatientListResponse(
        patients=[
            PatientListItemResponse(
                patient_id=patient_id,
                label=f"Patient {patient_id}",
            )
            for patient_id in patient_ids
        ]
    )


@router.get(
    "/{patient_id}",
    response_model=PatientSummaryResponse,
)
def get_patient(
    patient_id: int,
    settings: SettingsDependency,
) -> PatientSummaryResponse:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    try:
        patient_ids = discover_patient_ids(
            settings.patients_root
        )
    except (
        FileNotFoundError,
        NotADirectoryError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    if patient_id not in patient_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Patient {patient_id} "
                "was not found"
            ),
        )

    try:
        summary = (
            get_patient_catalog_summary(
                metadata_root=(
                    settings.metadata_root
                ),
                patient_id=patient_id,
            )
        )
    except (
        KeyError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return (
        PatientSummaryResponse.from_summary(
            summary
        )
    )