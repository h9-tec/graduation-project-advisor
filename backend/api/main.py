from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.routes import recommendations
from core.logging import configure_logging
from core.settings import get_settings


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(level=settings.log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Graduation Project Advisor",
        version="0.0.1",
        lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(recommendations.router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "grad-backend", "version": "0.0.1"}

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "env": settings.environment}

    @app.get("/metrics")
    async def metrics() -> PlainTextResponse:
        return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
