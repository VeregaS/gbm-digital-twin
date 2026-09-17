from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
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
from gbm_twin.api.schemas.viewer import (
    ViewerVolumeResponse,
)
from gbm_twin.workflows.cohort_evaluation import (
    CohortEvaluationResult,
    PatientEvaluationPayload,
)
from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
    summarize_cohort_evaluation,
)
from gbm_twin.workflows.twin_viewer import (
    TwinOverlayLayer,
    get_twin_viewer_volume_metadata,
    render_twin_viewer_slice_png,
)

router = APIRouter(
    prefix="/twin",
    tags=["twin"],
)

SettingsDependency = Annotated[
    ApiSettings,
    Depends(get_api_settings),
]

PlaneQuery = Literal[
    "axial",
    "coronal",
    "sagittal",
]

PlaneParameter = Annotated[
    PlaneQuery,
    Query(),
]

IndexParameter = Annotated[
    int | None,
    Query(ge=0),
]

LayerParameter = Annotated[
    TwinOverlayLayer,
    Query(),
]


def _require_twin_roots(
    settings: ApiSettings,
) -> tuple[Path, Path]:
    freeze_root = (
        settings.cohort_freeze_root
    )

    evaluation_root = (
        settings.cohort_evaluation_root
    )

    if freeze_root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cohort freeze root "
                "is not configured"
            ),
        )

    if evaluation_root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cohort evaluation root "
                "is not configured"
            ),
        )

    return (
        freeze_root,
        evaluation_root,
    )


def _load_evaluation(
    settings: ApiSettings,
) -> CohortEvaluationResult:
    _, evaluation_root = (
        _require_twin_roots(
            settings
        )
    )

    try:
        return (
            load_sealed_cohort_evaluation(
                evaluation_root
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
        evaluation.manifest["patients"]
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
        TwinCohortResponse.from_payload(
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
                    patient["patient_id"]
                ),
                target_timepoint=(
                    patient[
                        "target_timepoint"
                    ]
                ),
                target_day=(
                    patient["target_day"]
                ),
            )
            for patient
            in evaluation.manifest["patients"]
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


@router.get(
    "/patients/{patient_id}/viewer",
    response_model=ViewerVolumeResponse,
)
def get_twin_viewer(
    patient_id: int,
    settings: SettingsDependency,
) -> ViewerVolumeResponse:
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

    _find_patient(
        evaluation,
        patient_id,
    )

    _, evaluation_root = (
        _require_twin_roots(
            settings
        )
    )

    try:
        metadata = (
            get_twin_viewer_volume_metadata(
                metadata_root=(
                    settings.metadata_root
                ),
                patients_root=(
                    settings.patients_root
                ),
                cohort_evaluation_root=(
                    evaluation_root
                ),
                patient_id=patient_id,
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
        RuntimeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return (
        ViewerVolumeResponse
        .from_metadata(
            metadata
        )
    )


@router.get(
    "/patients/{patient_id}/slice",
)
def get_twin_slice(
    patient_id: int,
    settings: SettingsDependency,
    layer: LayerParameter = "twin",
    plane: PlaneParameter = "axial",
    index: IndexParameter = None,
) -> Response:
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

    _find_patient(
        evaluation,
        patient_id,
    )

    (
        freeze_root,
        evaluation_root,
    ) = _require_twin_roots(
        settings
    )

    try:
        png = (
            render_twin_viewer_slice_png(
                metadata_root=(
                    settings.metadata_root
                ),
                patients_root=(
                    settings.patients_root
                ),
                cohort_freeze_root=(
                    freeze_root
                ),
                cohort_evaluation_root=(
                    evaluation_root
                ),
                patient_id=patient_id,
                layer=layer,
                plane=plane,
                index=index,
            )
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except IndexError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except (
        KeyError,
        ValueError,
        RuntimeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": (
                "private, max-age=60"
            ),
        },
    )