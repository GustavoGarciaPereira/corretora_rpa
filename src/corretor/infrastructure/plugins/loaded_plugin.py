from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from corretor.domain.entities import AdapterManifest, PluginContext
from corretor.domain.ports import InsurerAdapter


@dataclass(frozen=True, slots=True)
class LoadedPlugin:
    manifest: AdapterManifest
    factory: Callable[[AdapterManifest, PluginContext], InsurerAdapter]
    source: str
