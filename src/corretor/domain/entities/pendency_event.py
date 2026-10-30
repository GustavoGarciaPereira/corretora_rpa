from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from corretor.domain.enums import WorkflowStatus


@dataclass(frozen=True, slots=True)
class PendencyEvent:
    to_status: WorkflowStatus
    from_status: WorkflowStatus | None = None
    note: str = ""
    created_at: datetime | None = None
    id: int | None = None
    pendency_id: int | None = None
