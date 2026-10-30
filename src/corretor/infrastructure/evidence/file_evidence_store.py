from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class FileEvidenceStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save(
        self,
        run_id: int,
        insurer_slug: str,
        payload: dict[str, Any],
        error: str | None = None,
    ) -> str:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self.base_dir / f"{run_id:06d}-{insurer_slug}.json"
        document = {
            "run_id": run_id,
            "insurer_slug": insurer_slug,
            "saved_at": datetime.now(UTC).isoformat(),
            "error": error,
            "payload": payload,
        }
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return str(path)
