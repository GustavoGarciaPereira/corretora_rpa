from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from corretor.infrastructure.config import Settings
from corretor.infrastructure.container import Container

from .filters import register_filters
from .routes import ROUTERS

logger = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)
    container = Container(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        container.initialize()
        container.start_scheduler()
        try:
            yield
        finally:
            container.shutdown()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.container = container

    base_dir = Path(__file__).resolve().parent
    app.mount(
        "/static",
        StaticFiles(directory=base_dir / "static"),
        name="static",
    )

    templates = Jinja2Templates(directory=base_dir / "templates")
    register_filters(templates.env)
    templates.env.globals["app_name"] = settings.app_name
    app.state.templates = templates

    for router in ROUTERS:
        app.include_router(router)

    return app
