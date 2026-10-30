from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Summary:
    total_open: int
    due_soon: int
    overdue: int
    failed_insurers: int
    total_insurers: int
