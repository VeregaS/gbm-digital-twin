from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
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
from gbm_twin.workflows.anatomy_runtime import (
    prepare_patient_atlas_preview,
)
from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
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



@router.post(
    "/{timepoint_name}/prepare",
    status_code=202,
)
def prepare_anatomical_risk(
    patient_id: int,
    timepoint_name: str,
    background_tasks: BackgroundTasks,
    settings: SettingsDependency,
) -> dict[str, str]:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    normalized_timepoint = (
        timepoint_name
        .strip()
        .lower()
    )

    if normalized_timepoint not in {
        "t0",
        "t1",
        "t2",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "timepoint_name must be "
                "t0, t1 or t2"
            ),
        )

    if settings.atlas_root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Atlas analysis is disabled."
            ),
        )

    background_tasks.add_task(
        prepare_patient_atlas_preview,
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
        timepoint_name=(
            normalized_timepoint
        ),
        target_spacing=(
            DEFAULT_TARGET_SPACING
        ),
    )

    return {
        "status": "preparing",
    }
