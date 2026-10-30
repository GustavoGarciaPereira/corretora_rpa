from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    NEEDS_ATTENTION = "AGUARDANDO_INTERVENCAO"

    @property
    def label(self) -> str:
        return {
            RunStatus.RUNNING: "Em execução",
            RunStatus.SUCCESS: "Sucesso",
            RunStatus.FAILED: "Falha",
            RunStatus.PARTIAL: "Parcial",
            RunStatus.NEEDS_ATTENTION: "Aguardando intervenção",
        }[self]

    @property
    def css_class(self) -> str:
        return {
            RunStatus.RUNNING: "running",
            RunStatus.SUCCESS: "success",
            RunStatus.FAILED: "failed",
            RunStatus.PARTIAL: "partial",
            RunStatus.NEEDS_ATTENTION: "attention",
        }[self]


FAILED_RUN_STATUSES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.FAILED,
        RunStatus.PARTIAL,
        RunStatus.NEEDS_ATTENTION,
    }
)
