from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

import corretor
from corretor.domain.enums import InsurerState
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store

router = APIRouter()

FAILED_STATES = {
    InsurerState.FAILED,
    InsurerState.PARTIAL,
    InsurerState.NEEDS_ATTENTION,
}


@router.get("/health")
@router.get("/healthz")
def healthz(
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
):
    database_ok = container.db.ping()
    health = store.list_insurer_health(container.stale_before())
    attention = [item.slug for item in health if item.state.needs_attention]
    stale = [item.slug for item in health if item.state is InsurerState.STALE]
    failed = [item.slug for item in health if item.state in FAILED_STATES]
    never_collected = [item.slug for item in health if item.state is InsurerState.NEVER_COLLECTED]
    plugin_errors = len(container.plugins.errors)
    status = "ok" if database_ok and not attention and not plugin_errors else "degraded"
    return JSONResponse(
        {
            "status": status,
            "version": corretor.__version__,
            "database": database_ok,
            "attention_insurers": attention,
            "stale_insurers": stale,
            "failed_insurers": failed,
            "never_collected_insurers": never_collected,
            "plugin_errors": plugin_errors,
        },
        status_code=200 if database_ok else 503,
    )
