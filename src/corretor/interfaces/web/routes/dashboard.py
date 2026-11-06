from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from corretor.application.dto import OPEN_FILTER
from corretor.domain.enums import RunStatus
from corretor.domain.errors import NotFoundError
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store, get_templates
from .common import filters_from_query, render_dashboard

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    insurer: str = "",
    status: str | None = None,
    q: str = "",
    kind: str = "",
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    filters = filters_from_query(insurer, status if status is not None else OPEN_FILTER, q, kind)
    partial = request.headers.get("HX-Request") == "true"
    return render_dashboard(templates, request, store, container, filters, partial=partial)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_partial(
    request: Request,
    insurer: str = "",
    status: str | None = None,
    q: str = "",
    kind: str = "",
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    filters = filters_from_query(insurer, status if status is not None else OPEN_FILTER, q, kind)
    return render_dashboard(templates, request, store, container, filters, partial=True)


@router.post("/collect", response_class=HTMLResponse)
def collect_now(
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    outcomes = container.collect_all()
    successes = sum(1 for outcome in outcomes if outcome.ok)
    failed_outcomes = [outcome for outcome in outcomes if not outcome.ok]
    attention = [outcome for outcome in outcomes if outcome.status is RunStatus.NEEDS_ATTENTION]
    if not outcomes:
        message = "Nenhuma seguradora ativa para coletar."
        kind = "warning"
    elif failed_outcomes:
        message = (
            f"Coleta concluída: {successes} sucesso(s), "
            f"{len(failed_outcomes)} falha(s). Detalhes abaixo."
        )
        kind = "warning" if successes else "error"
    else:
        message = f"Coleta concluída em {successes} seguradora(s)."
        kind = "success"
    return render_dashboard(
        templates,
        request,
        store,
        container,
        filters_from_query("", OPEN_FILTER, ""),
        partial=True,
        message=message,
        message_kind=kind,
        attention=attention,
    )


@router.post("/collect/{slug}", response_class=HTMLResponse)
def collect_one(
    slug: str,
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    try:
        outcome = container.collect(slug)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    attention = [outcome] if outcome.status is RunStatus.NEEDS_ATTENTION else []
    if outcome.ok:
        message = f"Coleta concluída: {outcome.insurer_name}."
        kind = "success"
    elif outcome.status is RunStatus.NEEDS_ATTENTION:
        message = f"Sessão expirada em {outcome.insurer_name}. Renove a conexão."
        kind = "warning"
    else:
        message = f"Falha ao coletar {outcome.insurer_name}. Detalhes abaixo."
        kind = "error"
    return render_dashboard(
        templates,
        request,
        store,
        container,
        filters_from_query("", OPEN_FILTER, ""),
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
        filters_from_query("", OPEN_FILTER, ""),
        partial=True,
        message=message,
        message_kind="success",
    )
