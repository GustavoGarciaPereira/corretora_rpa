from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from corretor.domain.entities import Policy
from corretor.domain.enums import PendencyKind

from .existing_installment import ExistingInstallment


@dataclass(frozen=True, slots=True)
class Snapshot:
    policies: dict[tuple[PendencyKind, str], Policy]
    items: dict[tuple[PendencyKind, str, int, date], ExistingInstallment]
