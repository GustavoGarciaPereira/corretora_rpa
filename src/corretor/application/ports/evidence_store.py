from __future__ import annotations

from typing import Any, Protocol


class EvidenceStore(Protocol):
    def save(
        self,
        run_id: int,
        insurer_slug: str,
        payload: dict[str, Any],
        error: str | None = None,
    ) -> str: ...
