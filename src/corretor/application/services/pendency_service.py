from __future__ import annotations

from corretor.domain.enums import WorkflowStatus
from corretor.domain.errors import NotFoundError

from ..dto import PendencyDetail, PendencyUpdate, PendencyView
from ..ports import Store


class PendencyService:
    def __init__(self, store: Store, clock) -> None:
        self.store = store
        self.clock = clock

    def update(self, pendency_id: int, update: PendencyUpdate, note: str = "") -> PendencyDetail:
        detail = self.store.update_pendency(
            pendency_id=pendency_id,
            update=update,
            note=note,
            now=self.clock.now(),
            today=self.clock.today(),
        )
        if detail is None:
            raise NotFoundError("pendência não encontrada")
        return detail

    def update_status(self, pendency_id: int, status: WorkflowStatus) -> PendencyView:
        view = self.store.update_status(
            pendency_id=pendency_id,
            status=status,
            now=self.clock.now(),
            today=self.clock.today(),
        )
        if view is None:
            raise NotFoundError("pendência não encontrada")
        return view

    def mark_overdue(self) -> int:
        return self.store.mark_overdue(self.clock.today(), self.clock.now())
