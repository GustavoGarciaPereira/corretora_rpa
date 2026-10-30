from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store
from .common import filters_from_query

router = APIRouter()

HEADERS = [
    "Seguradora",
    "Tipo",
    "Segurado",
    "Apólice",
    "Ramo",
    "Parcela",
    "Vencimento",
    "Valor (R$)",
    "Status",
    "Produtor",
    "Ação",
    "Novo vencimento",
    "Data limite",
    "Boleto",
    "Alertas",
]


@router.get("/export.csv")
def export_csv(
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
                row.insurer_name,
                row.kind.label,
                row.insured_name,
                row.policy_number,
                row.branch,
                row.installment_number,
                row.due_date.strftime("%d/%m/%Y"),
                f"{row.amount_cents / 100:.2f}".replace(".", ",") if row.amount_cents else "",
                row.workflow_status.label,
                row.producer,
                row.action,
                row.new_due_date.strftime("%d/%m/%Y") if row.new_due_date else "",
                row.deadline.strftime("%d/%m/%Y") if row.deadline else "",
                row.boleto_code,
                row.alerts,
            ]
        )
    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="parcelas-{container.clock.today().isoformat()}.csv"'
            )
        },
    )
