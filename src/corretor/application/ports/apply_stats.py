from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyStats:
    new_count: int
    resolved_count: int
