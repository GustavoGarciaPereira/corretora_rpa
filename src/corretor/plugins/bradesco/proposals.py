from __future__ import annotations

import re
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from corretor.domain.entities import RawInstallment
from corretor.domain.enums import PendencyKind
from corretor.domain.errors import AdapterError, ValidationError

DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")
MONEY_RE = re.compile(r"Valor\s+R\$\s*([\d.,]+)", re.IGNORECASE)


def _attr(row: Tag, name: str) -> str:
    value: Any = row.attrs.get(name, "")
    if isinstance(value, list):
        value = " ".join(str(item) for item in value)
    return str(value).strip()


def _text(row: Tag, selector: str) -> str:
    cell = row.select_one(selector)
    if cell is None:
        return ""
    return " ".join(cell.get_text(" ", strip=True).split())


def _parse_date(value: str, field: str) -> date:
    match = DATE_RE.search(value)
    if not match:
        raise ValidationError(f"{field} inválido: {value!r}")
    return datetime.strptime(match.group(0), "%d/%m/%Y").date()


def _amount_cents(value: str) -> int:
    text = value.strip()
    if not text:
        return 0
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValidationError(f"valor da proposta inválido: {value!r}") from exc
    if amount < 0:
        raise ValidationError("valor da proposta negativo")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _due_date(row: Tag) -> date:
    text = _text(row, "td.td-data-vencimento")
    if text:
        return _parse_date(text, "vencimento da 1ª parcela")

    # fallback: data-order do td-vencimento em epoch milissegundos
    cell = row.select_one("td.td-vencimento")
    if cell is not None:
        order = str(cell.attrs.get("data-order", "")).strip()
        if order.isdigit():
            return datetime.fromtimestamp(int(order) / 1000, tz=UTC).date()

    raise ValidationError("proposta sem data de vencimento")


def _policy_number(row: Tag) -> str:
    proposta = _attr(row, "data-proposta") or _attr(row, "data-codigo-proponente")
    if not proposta:
        raise ValidationError("proposta sem número")
    sucursal = _attr(row, "data-sucursal")
    agencia = _attr(row, "data-agencia")
    base = f"{sucursal}-{agencia}/{proposta}" if agencia else f"{sucursal}/{proposta}"
    return base


def _alerts(row: Tag) -> str:
    alerts: list[str] = []
    status = _attr(row, "data-vencimento-status")
    if status:
        alerts.append(f"1ª parcela: {status}")
    if _attr(row, "data-retificacao") not in {"", "0", "false", "False"}:
        alerts.append("Retificação pendente")
    if _attr(row, "data-vistoria-status") not in {"", "0"}:
        alerts.append("Vistoria")
    if _attr(row, "data-rastreador-status") not in {"", "0"}:
        alerts.append("Rastreador")
    return "; ".join(alerts)


def map_proposal_row(row: Tag) -> RawInstallment:
    insured_name = _attr(row, "data-nome-segurado") or _attr(row, "data-nome-segurado-formatado")
    if not insured_name:
        raise ValidationError("proposta sem nome do proponente")

    due_date = _due_date(row)
    amount = _attr(row, "data-valor-primeira-parcela")
    if not amount:
        match = MONEY_RE.search(_text(row, "td.td-vencimento"))
        amount = match.group(1) if match else "0"

    branch = _attr(row, "data-especialidade") or _attr(row, "data-ramo") or "Proposta"
    producer = _attr(row, "data-corretor") or _attr(row, "data-nome-corretor")

    return RawInstallment(
        policy_number=_policy_number(row),
        insured_name=insured_name,
        branch=branch,
        installment_number=1,
        due_date=due_date,
        amount_cents=_amount_cents(amount),
        producer=producer,
        boleto_code=_attr(row, "data-codigo-boleto"),
        external_id=_attr(row, "data-proposta"),
        alerts=_alerts(row),
        kind=PendencyKind.PROPOSTA,
    )


def parse_proposals_html(html: str) -> list[RawInstallment]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="propostas-pendentes")
    if table is None:
        table = soup.find("table", class_="tab-propostas")
    if table is None:
        text = soup.get_text(" ", strip=True).lower()
        if any(term in text for term in ("nenhuma proposta", "sem propostas", "não há propostas")):
            return []
        raise AdapterError("tabela de propostas pendentes não encontrada")

    rows = table.select("tbody tr[data-proposta]")
    expected = str(table.attrs.get("data-qtd-propostas-pendentes", "")).strip()
    if expected.isdigit() and int(expected) != len(rows):
        raise AdapterError(
            f"quantidade de propostas divergente: esperado {expected}, recebido {len(rows)}"
        )

    return [map_proposal_row(row) for row in rows]
