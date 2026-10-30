from __future__ import annotations

import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from corretor.domain.entities import RawInstallment
from corretor.domain.errors import AdapterError, ValidationError


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_date(value: Any, field: str) -> date:
    text = _text(value)
    if not text:
        raise ValidationError(f"{field} vazio")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValidationError(f"{field} inválido: {text!r}")


def _parse_optional_date(value: Any, field: str) -> date | None:
    text = _text(value)
    if not text:
        return None
    return _parse_date(text, field)


def _parse_int(value: Any, field: str) -> int:
    text = _text(value)
    match = re.search(r"\d+", text)
    if not match:
        raise ValidationError(f"{field} inválido: {text!r}")
    return int(match.group(0))


def _amount_cents(value: Any) -> int:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError("premio inválido") from exc
    if amount < 0:
        raise ValidationError("premio negativo")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _policy_number(parcela: dict[str, Any]) -> str:
    sucursal = _text(parcela.get("sucursal"))
    agencia = _text(parcela.get("agenciaProdutora"))
    apolice = _text(parcela.get("apolice"))
    item = _text(parcela.get("item"))
    endosso = _text(parcela.get("endosso"))

    if not apolice:
        raise ValidationError("apólice vazia")

    base = f"{sucursal}-{agencia}/{apolice}" if agencia else f"{sucursal}/{apolice}"
    detalhes = [part for part in (item, endosso) if part and part not in {"0", "00", "000"}]
    if detalhes:
        base = f"{base}/{'/'.join(detalhes)}"
    return base


def map_parcela(parcela: dict[str, Any]) -> RawInstallment:
    segurado = _dict(parcela.get("segurado"))
    corretor = _dict(parcela.get("corretor"))
    nome = _text(segurado.get("nome"))
    if not nome:
        raise ValidationError("segurado sem nome")

    modalidade = _text(parcela.get("modalidade"))
    ramo = _text(parcela.get("ramoSeguro"))
    branch = modalidade or (f"Ramo {ramo}" if ramo else "NÃO INFORMADO")

    alerts: list[str] = []
    if parcela.get("criticidade"):
        alerts.append("Com crítica")
    if parcela.get("sinistro"):
        alerts.append("Sinistro")
    if parcela.get("apoliceEmCancelamento"):
        alerts.append("Apólice em cancelamento")
    qtd_outras = _parse_int(parcela.get("qtdOutrasParcelas", 0), "qtdOutrasParcelas")
    if qtd_outras > 0:
        alerts.append(f"{qtd_outras} outra(s) parcela(s)")

    codigo_boleto = _text(parcela.get("parcSistemaCobranca"))
    dv = _text(parcela.get("dvParcSistemaCobranca"))
    if codigo_boleto and dv:
        codigo_boleto = f"{codigo_boleto}{dv}"

    producer = _text(corretor.get("codigo")) or _text(corretor.get("nome"))

    return RawInstallment(
        policy_number=_policy_number(parcela),
        insured_name=nome,
        branch=branch,
        installment_number=_parse_int(parcela.get("prestacao"), "prestacao"),
        due_date=_parse_date(parcela.get("vencimento"), "vencimento"),
        amount_cents=_amount_cents(parcela.get("premio", 0)),
        producer=producer,
        boleto_code=codigo_boleto,
        external_id=_text(parcela.get("idParcela")),
        deadline=_parse_optional_date(parcela.get("dataLimite"), "dataLimite"),
        alerts="; ".join(alerts),
    )


def map_payload(payload: Any) -> list[RawInstallment]:
    if not isinstance(payload, dict):
        raise AdapterError("payload do Bradesco não é um objeto JSON")

    situacao = payload.get("situacaoSistemas")
    if not isinstance(situacao, dict):
        raise AdapterError("payload sem 'situacaoSistemas'")
    if situacao.get("sistemasDisponiveis") is not True:
        mensagem = _text(situacao.get("mensagem")) or "sistemas indisponíveis"
        raise AdapterError(f"Bradesco indisponível: {mensagem}")

    parcelas = payload.get("parcelas")
    if not isinstance(parcelas, list):
        raise AdapterError("payload sem lista 'parcelas'")

    items: list[RawInstallment] = []
    for index, parcela in enumerate(parcelas):
        if not isinstance(parcela, dict):
            raise ValidationError(f"parcela {index} inválida")
        items.append(map_parcela(parcela))
    return items
