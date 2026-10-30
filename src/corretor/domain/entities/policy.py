from __future__ import annotations

from dataclasses import dataclass

from corretor.domain.enums import PendencyKind


@dataclass(frozen=True, slots=True)
class Policy:
    insurer_id: int
    policy_number: str
    insured_name: str
    branch: str
    producer: str = ""
    kind: PendencyKind = PendencyKind.PARCELA
    id: int | None = None
