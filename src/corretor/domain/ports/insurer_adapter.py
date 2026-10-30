from __future__ import annotations

from typing import Protocol

from corretor.domain.entities import AdapterManifest, RawInstallment


class InsurerAdapter(Protocol):
    manifest: AdapterManifest

    def fetch_pending(self) -> list[RawInstallment]:
        """Retorna um snapshot completo das parcelas pendentes.

        Deve levantar AdapterError (ou subclasse) em falha/parse parcial.
        """
        ...
