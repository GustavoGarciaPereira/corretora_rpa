from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from corretor.domain.enums import FAILED_RUN_STATUSES, RunStatus
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store, get_templates

router = APIRouter()

RENEW_BRADESCO = (
    "uv run python tools/discover_portal.py --slug bradesco "
    "--state data/sessions/bradesco.json --pause"
)


def _state(item) -> tuple[str, str]:
    if item.last_status is RunStatus.NEEDS_ATTENTION:
        return "expirada", "danger"
    if item.last_status in FAILED_RUN_STATUSES:
        return "falha", "warn"
    if item.is_stale:
        return "desatualizada", "warn"
    if item.last_success_at is None:
        return "sem coleta", "muted"
    return "ok", "success"


@router.get("/sessions", response_class=HTMLResponse)
def sessions(
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    health = store.list_insurer_health(container.stale_before())
    rows = []
    for item in health:
        label, badge = _state(item)
        rows.append({"health": item, "label": label, "badge": badge})

    return templates.TemplateResponse(
        request=request,
        name="sessions.html",
        context={
            "request": request,
            "rows": rows,
            "bradesco_state_exists": container.settings.bradesco_state_path.exists(),
            "bradesco_state_path": container.settings.bradesco_state_path,
            "renew_bradesco": RENEW_BRADESCO,
        },
    )
