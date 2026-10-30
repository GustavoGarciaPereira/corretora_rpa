from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from corretor.domain.enums import WorkflowStatus


@dataclass(frozen=True, slots=True)
class PendencyUpdate:
    workflow_status: WorkflowStatus
    action: str = ""
    new_due_date: date | None = None
    deadline: date | None = None
    assigned_to: str = ""
    notes: str = ""
