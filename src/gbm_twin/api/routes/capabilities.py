from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
)

from gbm_twin.api.config import (
    ApiSettings,
    get_api_settings,
)
from gbm_twin.api.schemas.capabilities import (
    CapabilitiesResponse,
    FeatureCapability,
)


router = APIRouter(
    prefix="/capabilities",
    tags=["capabilities"],
)


SettingsDependency = Annotated[
    ApiSettings,
    Depends(
        get_api_settings
    ),
]


def _yes() -> FeatureCapability:
    return FeatureCapability(
        available=True
    )


def _no(
    reason: str,
) -> FeatureCapability:
    return FeatureCapability(
        available=False,
        reason=reason,
    )


@router.get(
    "",
    response_model=CapabilitiesResponse,
)
def capabilities(
    settings: SettingsDependency,
) -> CapabilitiesResponse:
    dataset_ready = (
        settings.metadata_root.is_dir()
        and settings.patients_root.is_dir()
    )

    if dataset_ready:
        patients = _yes()
        viewer = _yes()
    else:
        reason = (
            "CFB-GBM dataset is not configured."
        )

        patients = _no(
            reason
        )

        viewer = _no(
            reason
        )

    atlas_root = (
        settings.atlas_root
    )

    anatomy_ready = (
        atlas_root is not None
        and (
            atlas_root
            / "manifest.json"
        ).is_file()
        and (
            atlas_root
            / "template_t1.nii.gz"
        ).is_file()
        and (
            atlas_root
            / "template_labels.nii.gz"
        ).is_file()
    )

    anatomy = (
        _yes()
        if anatomy_ready
        else _no(
            "Anatomical atlas is not configured."
        )
    )

    return CapabilitiesResponse(
        patients=patients,
        viewer=viewer,
        anatomy=anatomy,

        digital_twin=_no(
            "PatientTwin API is not "
            "exposed yet."
        ),

        runs=_no(
            "Run management is not "
            "implemented yet."
        ),

        tools=_no(
            "Tools workspace is not "
            "implemented yet."
        ),

        research=_no(
            "Research workspace is not "
            "implemented yet."
        ),
    )