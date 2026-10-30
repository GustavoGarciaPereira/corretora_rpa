from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from corretor.application.dto import (
    InsurerHealth,
    PendencyDetail,
    PendencyFilters,
    PendencyUpdate,
    PendencyView,
    RunView,
    Summary,
)
from corretor.domain.entities import CollectionRun, Insurer
from corretor.domain.enums import RunStatus, WorkflowStatus

from .apply_stats import ApplyStats
from .diff_result import DiffResult
from .snapshot import Snapshot


class Store(Protocol):
    def get_insurer_by_slug(self, slug: str) -> Insurer | None: ...

    def list_insurers(self) -> list[Insurer]: ...

    def list_active_insurers(self) -> list[Insurer]: ...

    def create_insurer(
        self, slug: str, name: str, adapter: str, active: bool = True
    ) -> Insurer: ...

    def start_run(self, insurer_id: int, started_at: datetime) -> CollectionRun: ...

    def finish_run(
        self,
        run_id: int,
        status: RunStatus,
        finished_at: datetime,
        items_found: int,
        new_count: int,
        resolved_count: int,
        error: str,
        evidence_path: str,
    ) -> None: ...

    def set_insurer_run_times(
        self, insurer_id: int, last_run_at: datetime, last_success_at: datetime | None
    ) -> None: ...

    def load_snapshot(self, insurer_id: int) -> Snapshot: ...

    def apply_diff(
        self, insurer_id: int, diff: DiffResult, collected_at: datetime
    ) -> ApplyStats: ...

    def list_pendencies(self, filters: PendencyFilters, today: date) -> list[PendencyView]: ...

    def summary(self, today: date, stale_before: datetime) -> Summary: ...

    def get_pendency_detail(self, pendency_id: int, today: date) -> PendencyDetail | None: ...

    def update_pendency(
        self,
        pendency_id: int,
        update: PendencyUpdate,
        note: str,
        now: datetime,
        today: date,
    ) -> PendencyDetail | None: ...

    def update_status(
        self,
        pendency_id: int,
        status: WorkflowStatus,
        now: datetime,
        today: date,
    ) -> PendencyView | None: ...

    def mark_overdue(self, today: date, now: datetime) -> int: ...

    def list_runs(self, limit: int = 20) -> list[RunView]: ...

    def list_insurer_health(self, stale_before: datetime) -> list[InsurerHealth]: ...
