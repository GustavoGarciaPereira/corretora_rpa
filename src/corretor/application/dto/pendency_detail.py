from __future__ import annotations

from dataclasses import dataclass

from corretor.domain.entities import PendencyEvent

from .pendency_view import PendencyView


@dataclass(frozen=True, slots=True)
class PendencyDetail:
    view: PendencyView
    notes: str
    events: tuple[PendencyEvent, ...]
    installment_id: int
