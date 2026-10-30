from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from corretor.domain.enums import WorkflowStatus


@dataclass(frozen=True, slots=True)
class Pendency:
    installment_id: int
    workflow_status: WorkflowStatus
    action: str = ""
    new_due_date: date | None = None
    deadline: date | None = None
    assigned_to: str = ""
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    id: int | None = None
