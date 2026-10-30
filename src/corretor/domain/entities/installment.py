from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from corretor.domain.enums import PendencyKind

INSTALLMENT_KEY = tuple[PendencyKind, str, int, date]


def installment_key(
    kind: PendencyKind, policy_number: str, number: int, due_date: date
) -> INSTALLMENT_KEY:
    return (kind, policy_number, number, due_date)


@dataclass(frozen=True, slots=True)
class Installment:
    policy_id: int
    number: int
    due_date: date
    amount_cents: int
    boleto_url: str = ""
    boleto_code: str = ""
    external_id: str = ""
    alerts: str = ""
    is_active: bool = True
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    id: int | None = None
