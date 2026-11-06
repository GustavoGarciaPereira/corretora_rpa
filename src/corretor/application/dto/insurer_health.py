from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from corretor.domain.enums import FAILED_RUN_STATUSES, RunStatus


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

    @property
    def is_failing(self) -> bool:
        return self.last_status is not None and self.last_status in FAILED_RUN_STATUSES
