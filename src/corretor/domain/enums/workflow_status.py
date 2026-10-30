from __future__ import annotations

from enum import StrEnum


class WorkflowStatus(StrEnum):
    DETECTADA = "DETECTADA"
    EM_ANALISE = "EM_ANALISE"
    AVISADA = "AVISADA"
    REGULARIZADA = "REGULARIZADA"
    VENCIDA = "VENCIDA"
    DESCARTADA = "DESCARTADA"

    @property
    def label(self) -> str:
        return {
            WorkflowStatus.DETECTADA: "Detectada",
            WorkflowStatus.EM_ANALISE: "Em análise",
            WorkflowStatus.AVISADA: "Avisada",
            WorkflowStatus.REGULARIZADA: "Regularizada",
            WorkflowStatus.VENCIDA: "Vencida",
            WorkflowStatus.DESCARTADA: "Descartada",
        }[self]

    @property
    def css_class(self) -> str:
        return {
            WorkflowStatus.DETECTADA: "detectada",
            WorkflowStatus.EM_ANALISE: "em-analise",
            WorkflowStatus.AVISADA: "avisada",
            WorkflowStatus.REGULARIZADA: "regularizada",
            WorkflowStatus.VENCIDA: "vencida",
            WorkflowStatus.DESCARTADA: "descartada",
        }[self]

    @property
    def is_open(self) -> bool:
        return self in OPEN_STATUSES


OPEN_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {
        WorkflowStatus.DETECTADA,
        WorkflowStatus.EM_ANALISE,
        WorkflowStatus.AVISADA,
    }
)

CLOSED_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {
        WorkflowStatus.REGULARIZADA,
        WorkflowStatus.VENCIDA,
        WorkflowStatus.DESCARTADA,
    }
)

REOPENABLE_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {
        WorkflowStatus.REGULARIZADA,
        WorkflowStatus.VENCIDA,
    }
)
