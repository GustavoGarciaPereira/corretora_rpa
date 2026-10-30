from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Insurer:
    slug: str
    name: str
    adapter: str
    active: bool = True
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None
    id: int | None = None
