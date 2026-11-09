from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
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

    @app.middleware("http")
    async def log_request_duration(request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        if not request.url.path.startswith("/static/"):
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "%s %s -> %s em %.0f ms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        return response

    base_dir = Path(__file__).resolve().parent
    static_dir = base_dir / "static"
    app.mount(
        "/static",
        StaticFiles(directory=static_dir),
        name="static",
    )

    templates = Jinja2Templates(directory=base_dir / "templates")
    register_filters(templates.env)
    templates.env.globals["app_name"] = settings.app_name
    try:
        asset_version = str(int((static_dir / "style.css").stat().st_mtime))
    except OSError:
        asset_version = "1"
    templates.env.globals["asset_version"] = asset_version
    app.state.templates = templates

    for router in ROUTERS:
        app.include_router(router)

    return app
