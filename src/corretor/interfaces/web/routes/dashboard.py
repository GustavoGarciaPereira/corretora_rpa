from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from corretor.domain.enums import RunStatus
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store, get_templates
from .common import filters_from_query, render_dashboard

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    insurer: str = "",
    status: str = "",
    q: str = "",
    kind: str = "",
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    filters = filters_from_query(insurer, status, q, kind)
    return render_dashboard(templates, request, store, container, filters, partial=False)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_partial(
    request: Request,
    insurer: str = "",
    status: str = "",
    q: str = "",
    kind: str = "",
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    filters = filters_from_query(insurer, status, q, kind)
    return render_dashboard(templates, request, store, container, filters, partial=True)


@router.post("/collect", response_class=HTMLResponse)
def collect_now(
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    outcomes = container.collection_service(store).collect_all()
    successes = sum(1 for outcome in outcomes if outcome.ok)
    failures = len(outcomes) - successes
    attention = [outcome for outcome in outcomes if outcome.status is RunStatus.NEEDS_ATTENTION]
    if not outcomes:
        message = "Nenhuma seguradora ativa para coletar."
        kind = "warning"
    elif failures:
        message = f"Coleta concluída: {successes} sucesso(s), {failures} falha(s)."
        kind = "warning" if successes else "error"
    else:
        message = f"Coleta concluída em {successes} seguradora(s)."
        kind = "success"
    return render_dashboard(
        templates,
        request,
        store,
        container,
        filters_from_query("", "", ""),
        partial=True,
        message=message,
        message_kind=kind,
        attention=attention,
    )


@router.post("/mark-overdue", response_class=HTMLResponse)
def mark_overdue(
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    count = container.pendency_service(store).mark_overdue()
    message = (
        f"{count} pendência(s) marcada(s) como vencida(s)."
        if count
        else "Nenhuma pendência nova para marcar como vencida."
    )
    return render_dashboard(
        templates,
        request,
        store,
        container,
        filters_from_query("", "", ""),
        partial=True,
        message=message,
        message_kind="success",
    )
