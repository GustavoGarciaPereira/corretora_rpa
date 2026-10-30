from __future__ import annotations

from typing import Protocol

from corretor.domain.entities import AdapterManifest
from corretor.domain.ports import InsurerAdapter


class AdapterProvider(Protocol):
    def get(self, slug: str) -> InsurerAdapter: ...

    def has(self, slug: str) -> bool: ...

    def manifests(self) -> list[AdapterManifest]: ...
