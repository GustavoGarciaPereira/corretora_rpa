from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AdapterManifest:
    slug: str
    name: str
    version: str
    description: str = ""
    mode: str = "python"
    status: str = "ready"
    capabilities: tuple[str, ...] = ("read_only",)
    requires_session: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", self.slug):
            raise ValueError(f"slug inválido: {self.slug!r}")
        if not self.name.strip():
            raise ValueError("name é obrigatório")
        if not self.version.strip():
            raise ValueError("version é obrigatória")
        if self.mode not in {"python", "recipe"}:
            raise ValueError(f"mode inválido: {self.mode!r}")
        if self.status not in {"ready", "discovery", "disabled"}:
            raise ValueError(f"status inválido: {self.status!r}")
        if not isinstance(self.capabilities, tuple):
            object.__setattr__(self, "capabilities", tuple(self.capabilities))
        if "read_only" not in self.capabilities:
            raise ValueError("todo adapter deve declarar a capability 'read_only'")
