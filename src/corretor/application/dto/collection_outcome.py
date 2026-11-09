from __future__ import annotations

from dataclasses import dataclass

from corretor.domain.enums import RunStatus


@dataclass(frozen=True, slots=True)
class CollectionOutcome:
    insurer_slug: str
    insurer_name: str
    status: RunStatus
    items_found: int = 0
    new_count: int = 0
    resolved_count: int = 0
    error: str = ""
    renewal_started: bool = False

    @property
    def ok(self) -> bool:
        return self.status is RunStatus.SUCCESS
