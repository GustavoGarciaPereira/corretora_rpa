from __future__ import annotations

from enum import StrEnum


class InsurerState(StrEnum):
    OK = "OK"
    RUNNING = "EM_EXECUCAO"
    FAILED = "FALHA"
    PARTIAL = "PARCIAL"
    NEEDS_ATTENTION = "AGUARDANDO_INTERVENCAO"
    STALE = "DESATUALIZADA"
    NEVER_COLLECTED = "SEM_COLETA"
    DISABLED = "DESATIVADA"

    @property
    def label(self) -> str:
        return {
            InsurerState.OK: "Em dia",
            InsurerState.RUNNING: "Em execução",
            InsurerState.FAILED: "Falha na coleta",
            InsurerState.PARTIAL: "Coleta parcial",
            InsurerState.NEEDS_ATTENTION: "Aguardando intervenção",
            InsurerState.STALE: "Dados desatualizados",
            InsurerState.NEVER_COLLECTED: "Sem coleta",
            InsurerState.DISABLED: "Desativada",
        }[self]

    @property
    def css_class(self) -> str:
        return {
            InsurerState.OK: "ok",
            InsurerState.RUNNING: "running",
            InsurerState.FAILED: "failed",
            InsurerState.PARTIAL: "partial",
            InsurerState.NEEDS_ATTENTION: "attention",
            InsurerState.STALE: "stale",
            InsurerState.NEVER_COLLECTED: "muted",
            InsurerState.DISABLED: "muted",
        }[self]

    @property
    def needs_attention(self) -> bool:
        return self in {
            InsurerState.FAILED,
            InsurerState.PARTIAL,
            InsurerState.NEEDS_ATTENTION,
            InsurerState.STALE,
            InsurerState.NEVER_COLLECTED,
        }
