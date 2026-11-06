from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from corretor.domain.enums import InsurerState, RunStatus


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
    def state(self) -> InsurerState:
        if not self.active:
            return InsurerState.DISABLED
        if self.last_status is RunStatus.RUNNING:
            return InsurerState.RUNNING
        if self.last_status is RunStatus.NEEDS_ATTENTION:
            return InsurerState.NEEDS_ATTENTION
        if self.last_status is RunStatus.PARTIAL:
            return InsurerState.PARTIAL
        if self.last_status is RunStatus.FAILED:
            return InsurerState.FAILED
        if self.last_success_at is None:
            if self.last_run_at is None:
                return InsurerState.NEVER_COLLECTED
            return InsurerState.FAILED
        if self.is_stale:
            return InsurerState.STALE
        return InsurerState.OK

    @property
    def is_failing(self) -> bool:
        return self.state in {
            InsurerState.FAILED,
            InsurerState.PARTIAL,
            InsurerState.NEEDS_ATTENTION,
        }
