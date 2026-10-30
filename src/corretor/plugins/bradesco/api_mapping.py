from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from corretor.domain.entities import RawInstallment
from corretor.domain.enums import PendencyKind
from corretor.domain.errors import AdapterError, ValidationError

BR_DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_date(value: Any, field: str) -> date:
    text = _text(value)
    match = BR_DATE_RE.search(text)
    if match:
        return datetime.strptime(match.group(0), "%d/%m/%Y").date()
    match = ISO_DATE_RE.search(text)
    if match:
        return datetime.strptime(match.group(0), "%Y-%m-%d").date()
    raise ValidationError(f"{field} inválido: {text!r}")


def _branch(proposta: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("tpProposta", "modalidade", "origem"):
        value = _text(proposta.get(key))
        if value and value not in parts:
            parts.append(value)
    return " / ".join(parts) or "Proposta"


def _alerts(proposta: dict[str, Any]) -> str:
    alerts: list[str] = []
    for critica in proposta.get("criticas") or []:
        if not isinstance(critica, dict):
            continue
        descricao = _text(critica.get("descricao"))
        causa = _text(critica.get("causa"))
        texto = descricao or causa
        if texto and texto not in alerts:
            alerts.append(texto)

    for key, label in (
        ("statusVistoria", "Vistoria"),
        ("statusRastreador", "Rastreador"),
        ("statusRetificacao", "Retificação"),
    ):
        value = _text(proposta.get(key))
        if value and value not in {"0", "00", "000"}:
            alerts.append(f"{label}: {value}")

    livelo = _dict(proposta.get("statusLivelo"))
    if livelo.get("pendente") is True:
        alerts.append("Livelo pendente")

    return "; ".join(alerts)


def _policy_number(proposta: dict[str, Any]) -> str:
    sucursal = _text(proposta.get("sucursal"))
    agencia = _text(proposta.get("agencia"))
    numero = _text(proposta.get("numProposta"))
    if not numero:
        raise ValidationError("proposta sem numProposta")
    if agencia:
        return f"{sucursal}-{agencia}/{numero}"
    return f"{sucursal}/{numero}"


def map_api_proposal(proposta: dict[str, Any]) -> RawInstallment:
    proponente = _dict(proposta.get("proponente"))
    nome = _text(proponente.get("nome"))
    if not nome:
        raise ValidationError("proposta sem nome do proponente")

    vencimento = _dict(proposta.get("vencimento"))
    due_date = _parse_date(vencimento.get("dtVencimento"), "vencimento")
    vigencia = _dict(proposta.get("vigencia"))
    start = _text(vigencia.get("dtInicioVigencia"))
    end = _text(vigencia.get("dtFimVigencia"))
    adjusted_vigency = f"{start} a {end}" if start and end else (start or end)

    return RawInstallment(
        policy_number=_policy_number(proposta),
        insured_name=nome,
        branch=_branch(proposta),
        installment_number=1,
        due_date=due_date,
        amount_cents=0,  # a API de propostas não devolve o valor da 1ª parcela
        producer="",
        boleto_code="",
        external_id=_text(proposta.get("numProposta")),
        alerts=_alerts(proposta),
        payment_method=_text(vencimento.get("formaPagamento")),
        adjusted_vigency=adjusted_vigency,
        insurer_status=_text(vencimento.get("status")),
        kind=PendencyKind.PROPOSTA,
    )


def map_api_payload(payload: Any) -> list[RawInstallment]:
    if not isinstance(payload, dict):
        raise AdapterError("resposta da API do Bradesco não é um objeto JSON")

    erro = payload.get("mensagemErro")
    if isinstance(erro, dict):
        descricao = _text(erro.get("dsErro"))
        if descricao:
            raise AdapterError(f"Bradesco API: {descricao}")

    propostas = payload.get("propostas")
    if not isinstance(propostas, list):
        raise AdapterError("resposta da API sem lista 'propostas'")

    items: list[RawInstallment] = []
    for index, proposta in enumerate(propostas):
        if not isinstance(proposta, dict):
            raise ValidationError(f"proposta {index} inválida")
        items.append(map_api_proposal(proposta))
    return items
