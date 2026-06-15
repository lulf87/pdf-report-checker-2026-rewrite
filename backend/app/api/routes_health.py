from fastapi import APIRouter, Request

from app.api.schemas.health import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    return HealthResponse(service=settings.app_service, version=settings.app_version)
