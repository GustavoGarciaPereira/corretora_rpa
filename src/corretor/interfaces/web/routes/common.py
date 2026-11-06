from __future__ import annotations

from datetime import date

from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates

from corretor.application.dto import CollectionOutcome, PendencyFilters
from corretor.domain.enums import PendencyKind, WorkflowStatus
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore


def filters_from_query(insurer: str, status: str, q: str, kind: str = "") -> PendencyFilters:
    return PendencyFilters(
        insurer_slug=insurer.strip(),
        status=status.strip(),
        q=q.strip(),
        kind=kind.strip(),
    )


def parse_status(value: str) -> WorkflowStatus:
    try:
        return WorkflowStatus(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Status inválido") from exc


def parse_optional_date(value: str, field: str = "data") -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field} inválida") from exc


def _error_items(health, failures: list[CollectionOutcome] | None) -> list[dict]:
    if failures is not None:
        return [
            {
                "slug": outcome.insurer_slug,
                "name": outcome.insurer_name,
                "status": outcome.status,
                "error": outcome.error or "Falha registrada sem mensagem de erro.",
                "when": None,
                "stale": False,
            }
            for outcome in failures
            if not outcome.ok
        ]
    return [
        {
            "slug": item.slug,
            "name": item.name,
            "status": item.last_status,
            "error": item.last_error or "Falha registrada sem mensagem de erro.",
            "when": item.last_run_at,
            "stale": item.is_stale,
        }
        for item in health
        if item.is_failing
    ]


def dashboard_context(
    request: Request,
    store: SqlAlchemyStore,
    container: Container,
    filters: PendencyFilters,
    message: str = "",
    message_kind: str = "success",
    failures: list[CollectionOutcome] | None = None,
) -> dict:
    today = container.clock.today()
    health = store.list_insurer_health(container.stale_before())
    return {
        "request": request,
        "pendencies": store.list_pendencies(filters, today),
        "summary": store.summary(today, container.stale_before()),
        "insurers": store.list_insurers(),
        "health": health,
        "health_by_slug": {item.slug: item for item in health},
        "runs": store.list_runs(6),
        "filters": filters,
        "statuses": list(WorkflowStatus),
        "kinds": list(PendencyKind),
        "today": today,
        "message": message,
        "message_kind": message_kind,
        "error_items": _error_items(health, failures),
    }


def render_dashboard(
    templates: Jinja2Templates,
    request: Request,
    store: SqlAlchemyStore,
    container: Container,
    filters: PendencyFilters,
    *,
    partial: bool,
    message: str = "",
    message_kind: str = "success",
    attention: list | None = None,
    failures: list[CollectionOutcome] | None = None,
):
    context = dashboard_context(
        request,
        store,
        container,
        filters,
        message=message,
        message_kind=message_kind,
        failures=failures,
    )
    context["attention"] = attention or []
    name = "partials/dashboard_content.html" if partial else "dashboard.html"
    return templates.TemplateResponse(request=request, name=name, context=context)
