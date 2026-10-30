from __future__ import annotations

from enum import StrEnum


class PendencyKind(StrEnum):
    PARCELA = "PARCELA"
    PROPOSTA = "PROPOSTA"

    @property
    def label(self) -> str:
        return {
            PendencyKind.PARCELA: "Parcela",
            PendencyKind.PROPOSTA: "Proposta",
        }[self]

    @property
    def css_class(self) -> str:
        return {
            PendencyKind.PARCELA: "parcela",
            PendencyKind.PROPOSTA: "proposta",
        }[self]
