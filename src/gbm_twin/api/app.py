from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gbm_twin.api.routes.health import (
    router as health_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="GBM Digital Twin Workbench",
        description=(
            "Research API for patient-specific "
            "glioblastoma digital twins."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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

    return app


app = create_app()