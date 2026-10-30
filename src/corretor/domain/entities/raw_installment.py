from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from corretor.domain.enums import PendencyKind


@dataclass(frozen=True, slots=True)
class RawInstallment:
    policy_number: str
    insured_name: str
    branch: str
    installment_number: int
    due_date: date
    amount_cents: int
    producer: str = ""
    boleto_url: str = ""
    boleto_code: str = ""
    external_id: str = ""
    deadline: date | None = None
    alerts: str = ""
    kind: PendencyKind = PendencyKind.PARCELA
