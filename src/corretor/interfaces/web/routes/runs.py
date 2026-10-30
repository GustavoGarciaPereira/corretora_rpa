from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_store, get_templates

router = APIRouter()


@router.get("/runs", response_class=HTMLResponse)
def runs(
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    templates: Jinja2Templates = Depends(get_templates),
):
    return templates.TemplateResponse(
        request=request,
        name="runs.html",
        context={"request": request, "runs": store.list_runs(50)},
    )
