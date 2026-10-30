from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store, get_templates
from .common import dashboard_context, filters_from_query

router = APIRouter()

HEADERS = [
    "DATA AÇÃO",
    "CIA",
    "TIPO",
    "SEGURADO",
    "RAMO",
    "FORMA PAGTO",
    "VENCIMENTO",
    "PARCELA PENDENTE",
    "VIGENCIA AJUSTADA",
    "AÇÃO",
    "PRODUTOR",
    "NOVO VENC",
    "DATA LIMITE",
    "STATUS",
]


@router.get("/planilha", response_class=HTMLResponse)
def planilha(
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
    context = dashboard_context(request, store, container, filters)
    return templates.TemplateResponse(request=request, name="planilha.html", context=context)


@router.get("/export-planilha.csv")
def export_planilha(
    request: Request,
    insurer: str = "",
    status: str = "",
    q: str = "",
    kind: str = "",
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
):
    filters = filters_from_query(insurer, status, q, kind)
    rows = store.list_pendencies(filters, container.clock.today())
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(HEADERS)
    for row in rows:
        writer.writerow(
            [
                row.action_date.strftime("%d/%m/%Y") if row.action_date else "",
                row.insurer_name,
                row.kind.label,
                row.insured_name,
                row.branch,
                row.payment_method,
                row.due_date.strftime("%d/%m/%Y"),
                row.installment_number,
                row.adjusted_vigency,
                row.action,
                row.producer,
                row.new_due_date.strftime("%d/%m/%Y") if row.new_due_date else "",
                row.deadline.strftime("%d/%m/%Y") if row.deadline else "",
                row.spreadsheet_status,
            ]
        )
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="controle-parcelas-'
                f'{container.clock.today().isoformat()}.csv"'
            )
        },
    )
