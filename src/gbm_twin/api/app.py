from fastapi import FastAPI
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from gbm_twin.api.config import (
    ApiSettings,
)
from gbm_twin.api.routes.anatomy import (
    router as anatomy_router,
)
from gbm_twin.api.routes.capabilities import (
    router as capabilities_router,
)
from gbm_twin.api.routes.health import (
    router as health_router,
)
from gbm_twin.api.routes.patients import (
    router as patients_router,
)
from gbm_twin.api.routes.twin import (
    router as twin_router,
)
from gbm_twin.api.routes.twin_analysis import (
    router as twin_analysis_router,
)
from gbm_twin.api.routes.viewer import (
    router as viewer_router,
)


def create_app(
    settings: ApiSettings | None = None,
) -> FastAPI:
    app = FastAPI(
        title=(
            "GBM Digital Twin Workbench"
        ),
        description=(
            "Research API for "
            "patient-specific glioblastoma "
            "digital twins."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.state.settings = (
        settings
        if settings is not None
        else ApiSettings.from_environment()
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(
        health_router,
        prefix="/api",
    )

    app.include_router(
        patients_router,
        prefix="/api",
    )

    app.include_router(
        twin_router,
        prefix="/api",
    )

    app.include_router(
        twin_analysis_router,
        prefix="/api",
    )

    app.include_router(
        viewer_router,
        prefix="/api",
    )

    app.include_router(
        anatomy_router,
        prefix="/api",
    )

    app.include_router(
        capabilities_router,
        prefix="/api",
    )

    return app


app = create_app()
