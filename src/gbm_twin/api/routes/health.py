from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/health",
    tags=["system"],
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get(
    "",
    response_model=HealthResponse,
)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="gbm-digital-twin-workbench",
        version="0.1.0",
    )