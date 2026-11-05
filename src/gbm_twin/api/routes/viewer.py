from __future__ import annotations

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
from gbm_twin.api.schemas.scene3d import (
    Viewer3DSceneResponse,
)
from gbm_twin.api.schemas.viewer import (
    ViewerVolumeResponse,
)
from gbm_twin.api.schemas.viewer_focus import (
    ViewerFocusResponse,
)
from gbm_twin.workflows.scene3d import (
    get_viewer_3d_scene,
)
from gbm_twin.workflows.viewer import (
    get_viewer_volume_metadata,
    render_viewer_slice_png,
)
from gbm_twin.workflows.viewer_focus import (
    get_viewer_focus_metadata,
)

router = APIRouter(
    prefix="/patients/{patient_id}/viewer",
    tags=["viewer"],
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

OverlayParameter = Annotated[
    bool,
    Query(),
]


@router.get(
    "/{timepoint_name}",
    response_model=ViewerVolumeResponse,
)
def get_viewer_metadata(
    patient_id: int,
    timepoint_name: str,
    settings: SettingsDependency,
) -> ViewerVolumeResponse:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    try:
        metadata = (
            get_viewer_volume_metadata(
                metadata_root=(
                    settings.metadata_root
                ),
                patients_root=(
                    settings.patients_root
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
        ViewerVolumeResponse.from_metadata(
            metadata
        )
    )


@router.get(
    "/{timepoint_name}/focus",
    response_model=ViewerFocusResponse,
)
def get_viewer_focus(
    patient_id: int,
    timepoint_name: str,
    settings: SettingsDependency,
) -> ViewerFocusResponse:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    try:
        metadata = (
            get_viewer_focus_metadata(
                metadata_root=(
                    settings.metadata_root
                ),
                patients_root=(
                    settings.patients_root
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
        ViewerFocusResponse.from_metadata(
            metadata
        )
    )


@router.get(
    "/{timepoint_name}/slice",
)
def get_viewer_slice(
    patient_id: int,
    timepoint_name: str,
    settings: SettingsDependency,
    plane: PlaneParameter = "axial",
    index: IndexParameter = None,
    overlay_gtv: OverlayParameter = True,
) -> Response:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    try:
        png = render_viewer_slice_png(
            metadata_root=(
                settings.metadata_root
            ),
            patients_root=(
                settings.patients_root
            ),
            patient_id=patient_id,
            timepoint_name=(
                timepoint_name
            ),
            plane=plane,
            index=index,
            overlay_gtv=overlay_gtv,
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
    "/{timepoint_name}/scene3d",
    response_model=Viewer3DSceneResponse,
)
def get_viewer_scene_3d(
    patient_id: int,
    timepoint_name: str,
    settings: SettingsDependency,
) -> Viewer3DSceneResponse:
    if patient_id <= 0:
        raise HTTPException(
            status_code=422,
            detail=(
                "patient_id must be positive"
            ),
        )

    try:
        scene = get_viewer_3d_scene(
            metadata_root=(
                settings.metadata_root
            ),
            patients_root=(
                settings.patients_root
            ),
            patient_id=patient_id,
            timepoint_name=(
                timepoint_name
            ),
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
        Viewer3DSceneResponse
        .from_scene(
            scene
        )
    )
