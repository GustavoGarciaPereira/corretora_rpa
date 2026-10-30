from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from corretor.domain.entities import RawInstallment, installment_key
from corretor.domain.enums import PendencyKind
from corretor.domain.errors import ValidationError


def normalize_items(raw_items: Iterable[RawInstallment]) -> list[RawInstallment]:
    """Valida e normaliza o snapshot retornado por um adapter.

    Um snapshot inválido deve falhar por inteiro: é melhor marcar a coleta
    como falha do que gravar dados parciais/corrompidos.
    """
    normalized: list[RawInstallment] = []
    seen: set[tuple[str, int, date]] = set()

    for raw in raw_items:
        policy_number = str(raw.policy_number).strip()
        insured_name = str(raw.insured_name).strip()
        branch = str(raw.branch).strip() or "NÃO INFORMADO"
        producer = str(raw.producer or "").strip()
        boleto_url = str(raw.boleto_url or "").strip()
        boleto_code = str(raw.boleto_code or "").strip()
        external_id = str(raw.external_id or "").strip()
        alerts = str(raw.alerts or "").strip()
        payment_method = str(raw.payment_method or "").strip()
        adjusted_vigency = str(raw.adjusted_vigency or "").strip()
        insurer_status = str(raw.insurer_status or "").strip()

        if not policy_number:
            raise ValidationError("parcela sem número de apólice")
        if not insured_name:
            raise ValidationError("parcela sem nome do segurado")
        try:
            number = int(raw.installment_number)
        except (TypeError, ValueError) as exc:
            raise ValidationError("número de parcela inválido") from exc
        if number < 1:
            raise ValidationError("número de parcela deve ser >= 1")
        try:
            amount_cents = int(raw.amount_cents)
        except (TypeError, ValueError) as exc:
            raise ValidationError("valor da parcela inválido") from exc
        if amount_cents < 0:
            raise ValidationError("valor da parcela não pode ser negativo")

        if not isinstance(raw.due_date, date) or isinstance(raw.due_date, datetime):
            raise ValidationError("vencimento inválido")
        if raw.deadline is not None and (
            not isinstance(raw.deadline, date) or isinstance(raw.deadline, datetime)
        ):
            raise ValidationError("data limite inválida")
        try:
            kind = PendencyKind(raw.kind)
        except ValueError as exc:
            raise ValidationError("tipo de pendência inválido") from exc

        key = installment_key(kind, policy_number, number, raw.due_date)
        if key in seen:
            raise ValidationError("parcela duplicada no snapshot")
        seen.add(key)

        normalized.append(
            RawInstallment(
                policy_number=policy_number,
                insured_name=insured_name,
                branch=branch,
                installment_number=number,
                due_date=raw.due_date,
                amount_cents=amount_cents,
                producer=producer,
                boleto_url=boleto_url,
                boleto_code=boleto_code,
                external_id=external_id,
                deadline=raw.deadline,
                alerts=alerts,
                payment_method=payment_method,
                adjusted_vigency=adjusted_vigency,
                insurer_status=insurer_status,
                kind=kind,
            )
        )

    return normalized
