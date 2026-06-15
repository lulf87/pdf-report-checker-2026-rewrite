from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_health import router as health_router
from app.api.routes_ptr_compare import router as ptr_compare_router
from app.api.routes_report_check import router as report_check_router
from app.api.routes_tasks import router as tasks_router
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    logger = setup_logging(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("Application startup")
        yield
        logger.info("Application shutdown")

    app = FastAPI(
        title=app_settings.app_name,
        description=app_settings.app_description,
        version=app_settings.app_version,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(report_check_router)
    app.include_router(ptr_compare_router)
    app.include_router(tasks_router)
    return app


app = create_app()
