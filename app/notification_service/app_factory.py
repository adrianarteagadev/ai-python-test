from __future__ import annotations

from contextlib import asynccontextmanager

import logging

from fastapi import FastAPI

from notification_service.api.router import router
from notification_service.infrastructure.runtime import build_container, load_settings
from notification_service.infrastructure.settings import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = build_container(settings)
        app.state.container = container
        await container.start()
        try:
            yield
        finally:
            await container.stop()

    app = FastAPI(
        title="Notification Service (Technical Test)",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app
