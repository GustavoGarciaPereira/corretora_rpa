from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from corretor.domain.enums import RunStatus


@dataclass(frozen=True, slots=True)
class CollectionRun:
    insurer_id: int
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    items_found: int = 0
    new_count: int = 0
    resolved_count: int = 0
    error: str = ""
    evidence_path: str = ""
    id: int | None = None
