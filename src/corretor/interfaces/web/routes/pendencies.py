from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from corretor.application.dto import PendencyUpdate
from corretor.domain.enums import WorkflowStatus
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store, get_templates
from .common import parse_optional_date, parse_status

router = APIRouter()


@router.get("/pendencies/{pendency_id}", response_class=HTMLResponse)
def detail(
    pendency_id: int,
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    detail_data = store.get_pendency_detail(pendency_id, container.clock.today())
    if detail_data is None:
        raise HTTPException(status_code=404, detail="Pendência não encontrada")
    return templates.TemplateResponse(
        request=request,
        name="detail.html",
        context={
            "request": request,
            "detail": detail_data,
            "statuses": list(WorkflowStatus),
            "saved": request.query_params.get("saved") == "1",
        },
    )


@router.post("/pendencies/{pendency_id}")
def update(
    pendency_id: int,
    workflow_status: str = Form(...),
    action: str = Form(""),
    action_date: str = Form(""),
    new_due_date: str = Form(""),
    deadline: str = Form(""),
    assigned_to: str = Form(""),
    notes: str = Form(""),
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
):
    update_data = PendencyUpdate(
        workflow_status=parse_status(workflow_status),
        action=action.strip(),
        action_date=parse_optional_date(action_date, "data da ação"),
        new_due_date=parse_optional_date(new_due_date, "novo vencimento"),
        deadline=parse_optional_date(deadline, "data limite"),
        assigned_to=assigned_to.strip(),
        notes=notes.strip(),
    )
    service = container.pendency_service(store)
    service.update(pendency_id, update_data, note="")
    return RedirectResponse(url=f"/pendencies/{pendency_id}?saved=1", status_code=303)


@router.post("/pendencies/{pendency_id}/status", response_class=HTMLResponse)
def update_status(
    pendency_id: int,
    request: Request,
    workflow_status: str = Form(...),
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    view = container.pendency_service(store).update_status(
        pendency_id, parse_status(workflow_status)
    )
    return templates.TemplateResponse(
        request=request,
        name="partials/row.html",
        context={
            "request": request,
            "p": view,
            "statuses": list(WorkflowStatus),
        },
    )
