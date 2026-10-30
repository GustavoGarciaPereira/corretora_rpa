from __future__ import annotations

from dataclasses import dataclass

OPEN_FILTER = "ABERTAS"
OVERDUE_FILTER = "VENCIDAS"


@dataclass(frozen=True, slots=True)
class PendencyFilters:
    insurer_slug: str = ""
    status: str = ""
    q: str = ""
    kind: str = ""

    @property
    def is_overdue_only(self) -> bool:
        return self.status == OVERDUE_FILTER
