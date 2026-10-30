from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


class SystemClock:
    def __init__(self, timezone_name: str = "America/Sao_Paulo") -> None:
        self.timezone = ZoneInfo(timezone_name)

    def now(self) -> datetime:
        """UTC sem tzinfo (compatível com SQLite)."""
        return datetime.now(UTC).replace(tzinfo=None)

    def today(self) -> date:
        return datetime.now(self.timezone).date()
