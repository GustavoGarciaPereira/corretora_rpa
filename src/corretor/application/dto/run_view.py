from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from corretor.domain.enums import RunStatus


@dataclass(frozen=True, slots=True)
class RunView:
    id: int
    insurer_name: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None
    items_found: int
    new_count: int
    resolved_count: int
    error: str
    evidence_path: str
