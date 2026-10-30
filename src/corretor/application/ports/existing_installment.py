from __future__ import annotations

from dataclasses import dataclass

from corretor.domain.entities import Installment, Pendency
from corretor.domain.enums import PendencyKind


@dataclass(frozen=True, slots=True)
class ExistingInstallment:
    kind: PendencyKind
    policy_number: str
    installment: Installment
    pendency: Pendency
