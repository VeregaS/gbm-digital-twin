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
from gbm_twin.api.schemas.anatomy import (
    AnatomicalRiskResponse,
)
from gbm_twin.workflows.anatomy import (
    analyze_patient_anatomy,
)

router = APIRouter(
    prefix="/patients/{patient_id}/anatomy",
    tags=["anatomy"],
)


SettingsDependency = Annotated[
    ApiSettings,
    Depends(get_api_settings),
]


@router.get(
    "/{timepoint_name}",
    response_model=(
        AnatomicalRiskResponse
    ),
)
def get_anatomical_risk(
    patient_id: int,
    timepoint_name: str,
    settings: SettingsDependency,
) -> AnatomicalRiskResponse:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must "
                "be positive"
            ),
        )

    try:
        report = (
            analyze_patient_anatomy(
                metadata_root=(
                    settings
                    .metadata_root
                ),
                patients_root=(
                    settings
                    .patients_root
                ),
                atlas_root=(
                    settings
                    .atlas_root
                ),
                patient_id=patient_id,
                timepoint_name=(
                    timepoint_name
                ),
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except (
        KeyError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return (
        AnatomicalRiskResponse
        .from_report(
            report
        )
    )