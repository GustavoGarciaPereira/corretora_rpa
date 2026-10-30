from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from corretor.domain.enums import RunStatus


@dataclass(frozen=True, slots=True)
class InsurerHealth:
    slug: str
    name: str
    active: bool
    last_run_at: datetime | None
    last_success_at: datetime | None
    is_stale: bool
    last_status: RunStatus | None
    last_error: str
