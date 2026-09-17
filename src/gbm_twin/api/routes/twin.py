from __future__ import annotations

import csv
from io import StringIO
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
from gbm_twin.api.schemas.twin_qc import (
    TwinPatientQCResponse,
)
from gbm_twin.api.schemas.twin_scene3d import (
    TwinViewer3DSceneResponse,
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
from gbm_twin.workflows.twin_qc import (
    get_twin_patient_qc,
)
from gbm_twin.workflows.twin_scene3d import (
    get_twin_viewer_3d_scene,
)
from gbm_twin.workflows.twin_viewer import (
    TwinComparisonMode,
    TwinOverlayLayer,
    TwinPredictionMethod,
    get_twin_viewer_volume_metadata,
    render_twin_comparison_slice_png,
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

MethodParameter = Annotated[
    TwinPredictionMethod,
    Query(),
]

ComparisonModeParameter = Annotated[
    TwinComparisonMode,
    Query(),
]


def _require_twin_roots(
    settings: ApiSettings,
) -> tuple[
    Path,
    Path,
]:
    freeze_root = (
        settings.cohort_freeze_root
    )

    evaluation_root = (
        settings
        .cohort_evaluation_root
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
    "/evaluations",
    response_model=list[
        TwinPatientEvaluationResponse
    ],
)
def list_twin_evaluations(
    settings: SettingsDependency,
) -> list[
    TwinPatientEvaluationResponse
]:
    evaluation = (
        _load_evaluation(
            settings
        )
    )

    return [
        TwinPatientEvaluationResponse
        .from_payload(
            patient
        )
        for patient
        in evaluation.manifest[
            "patients"
        ]
    ]


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

@router.get(
    "/patients/{patient_id}/compare-slice",
)
def get_twin_comparison_slice(
    patient_id: int,
    settings: SettingsDependency,
    method: MethodParameter = "twin",
    mode: ComparisonModeParameter = "overlay",
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
            render_twin_comparison_slice_png(
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
                method=method,
                comparison_mode=mode,
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


@router.get(
    "/patients/{patient_id}/qc",
    response_model=(
        TwinPatientQCResponse
    ),
)
def get_twin_qc(
    patient_id: int,
    settings: SettingsDependency,
) -> TwinPatientQCResponse:
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
        qc = get_twin_patient_qc(
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
        TwinPatientQCResponse
        .from_qc(
            qc
        )
    )


@router.get(
    "/patients/{patient_id}/scene3d",
    response_model=(
        TwinViewer3DSceneResponse
    ),
)
def get_twin_scene_3d(
    patient_id: int,
    settings: SettingsDependency,
) -> TwinViewer3DSceneResponse:
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
        scene = (
            get_twin_viewer_3d_scene(
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
        TwinViewer3DSceneResponse
        .from_scene(
            scene
        )
    )


@router.get(
    "/export/evaluation.json",
)
def export_twin_evaluation_json(
    settings: SettingsDependency,
) -> Response:
    _load_evaluation(
        settings
    )

    _, evaluation_root = (
        _require_twin_roots(
            settings
        )
    )

    manifest_path = (
        evaluation_root.resolve()
        / "cohort_evaluation.json"
    )

    content = (
        manifest_path.read_bytes()
    )

    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="'
                "cohort_evaluation.json"
                '"'
            ),
        },
    )


@router.get(
    "/export/evaluation.csv",
)
def export_twin_evaluation_csv(
    settings: SettingsDependency,
) -> Response:
    evaluation = (
        _load_evaluation(
            settings
        )
    )

    buffer = StringIO(
        newline=""
    )

    writer = csv.writer(
        buffer,
        lineterminator="\n",
    )

    writer.writerow(
        [
            "patient_id",
            "target_timepoint",
            "target_day",
            "twin_dice",
            "twin_relative_volume_error",
            "twin_hd95_mm",
            "twin_centroid_distance_mm",
            "persistence_dice",
            "persistence_relative_volume_error",
            "persistence_hd95_mm",
            "persistence_centroid_distance_mm",
            "volume_baseline_dice",
            "volume_baseline_relative_volume_error",
            "volume_baseline_hd95_mm",
            "volume_baseline_centroid_distance_mm",
        ]
    )

    for patient in (
        evaluation
        .manifest["patients"]
    ):
        twin = patient["twin"]

        persistence = (
            patient["persistence"]
        )

        volume_baseline = (
            patient[
                "volume_baseline"
            ]
        )

        writer.writerow(
            [
                patient["patient_id"],
                patient[
                    "target_timepoint"
                ],
                patient["target_day"],
                twin["dice"],
                twin[
                    "relative_volume_error"
                ],
                twin["hd95_mm"],
                twin[
                    "centroid_distance_mm"
                ],
                persistence["dice"],
                persistence[
                    "relative_volume_error"
                ],
                persistence[
                    "hd95_mm"
                ],
                persistence[
                    "centroid_distance_mm"
                ],
                volume_baseline[
                    "dice"
                ],
                volume_baseline[
                    "relative_volume_error"
                ],
                volume_baseline[
                    "hd95_mm"
                ],
                volume_baseline[
                    "centroid_distance_mm"
                ],
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="'
                "cohort_evaluation.csv"
                '"'
            ),
        },
    )