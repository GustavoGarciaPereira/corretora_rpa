from __future__ import annotations

from dataclasses import dataclass

from corretor.domain.entities import RawInstallment

from .existing_installment import ExistingInstallment


@dataclass(frozen=True, slots=True)
class DiffResult:
    incoming: tuple[RawInstallment, ...]
    new: tuple[RawInstallment, ...]
    reopened: tuple[RawInstallment, ...]
    missing: tuple[ExistingInstallment, ...]
    discarded_reappeared: tuple[RawInstallment, ...]

    @property
    def new_count(self) -> int:
        return len(self.new)

    @property
    def resolved_count(self) -> int:
        return sum(1 for item in self.missing if item.pendency.workflow_status.is_open)
