from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import corretor
from corretor.domain.enums import FAILED_RUN_STATUSES
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store

router = APIRouter()


@router.get("/healthz")
def healthz(
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
):
    database_ok = container.db.ping()
    health = store.list_insurer_health(container.stale_before())
    stale = [item.slug for item in health if item.is_stale]
    failed = [item.slug for item in health if item.last_status in FAILED_RUN_STATUSES]
    plugin_errors = len(container.plugins.errors)
    status = "ok" if database_ok and not stale and not failed and not plugin_errors else "degraded"
    return JSONResponse(
        {
            "status": status,
            "version": corretor.__version__,
            "database": database_ok,
            "stale_insurers": stale,
            "failed_insurers": failed,
            "plugin_errors": plugin_errors,
        },
        status_code=200 if database_ok else 503,
    )
