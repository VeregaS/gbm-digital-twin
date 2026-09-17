from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
)

from gbm_twin.api.config import (
    ApiSettings,
    get_api_settings,
)
from gbm_twin.api.schemas.twin_analysis import (
    TwinCohortAnalysisResponse,
)
from gbm_twin.workflows.cohort_analysis import (
    CohortErrorAnalysisResult,
    load_sealed_cohort_analysis,
)
from gbm_twin.workflows.provenance import (
    sha256_file,
)

router = APIRouter(
    prefix="/twin/analysis",
    tags=["twin-analysis"],
)

SettingsDependency = Annotated[
    ApiSettings,
    Depends(get_api_settings),
]


def _require_analysis_root(
    settings: ApiSettings,
) -> Path:
    root = settings.cohort_analysis_root

    if root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cohort analysis root is not configured"
            ),
        )

    return root


def _require_evaluation_root(
    settings: ApiSettings,
) -> Path:
    root = settings.cohort_evaluation_root

    if root is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Cohort evaluation root is not configured"
            ),
        )

    return root


def _load_current_analysis(
    settings: ApiSettings,
) -> CohortErrorAnalysisResult:
    analysis_root = _require_analysis_root(
        settings
    )

    evaluation_root = _require_evaluation_root(
        settings
    )

    try:
        result = load_sealed_cohort_analysis(
            analysis_root
        )

        evaluation_path = (
            evaluation_root.resolve()
            / "cohort_evaluation.json"
        )

        if not evaluation_path.is_file():
            raise FileNotFoundError(
                "Source cohort evaluation manifest not found: "
                f"{evaluation_path}"
            )

        expected_sha = result.manifest.get(
            "source_evaluation_sha256"
        )

        if not isinstance(
            expected_sha,
            str,
        ):
            raise ValueError(
                "Cohort analysis is missing source evaluation SHA-256"
            )

        actual_sha = sha256_file(
            evaluation_path
        )

        if actual_sha != expected_sha:
            raise ValueError(
                "Cohort analysis is stale: source evaluation has changed"
            )

        return result

    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=TwinCohortAnalysisResponse,
)
def get_twin_cohort_analysis(
    settings: SettingsDependency,
) -> TwinCohortAnalysisResponse:
    result = _load_current_analysis(
        settings
    )

    return TwinCohortAnalysisResponse.model_validate(
        result.manifest
    )


@router.get(
    "/export.json",
)
def export_twin_cohort_analysis_json(
    settings: SettingsDependency,
) -> Response:
    result = _load_current_analysis(
        settings
    )

    path = (
        result.directory
        / "cohort_analysis.json"
    )

    return Response(
        content=path.read_bytes(),
        media_type="application/json",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="cohort_analysis.json"'
            ),
        },
    )


@router.get(
    "/export.csv",
)
def export_twin_cohort_analysis_csv(
    settings: SettingsDependency,
) -> Response:
    result = _load_current_analysis(
        settings
    )

    path = (
        result.directory
        / "cohort_analysis.csv"
    )

    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "Cohort analysis CSV is missing"
            ),
        )

    return Response(
        content=path.read_bytes(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="cohort_analysis.csv"'
            ),
        },
    )
