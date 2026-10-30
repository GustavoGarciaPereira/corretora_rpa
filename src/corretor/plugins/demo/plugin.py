from __future__ import annotations

from corretor.domain.entities import AdapterManifest, PluginContext

from .adapter import DemoAdapter


def create_adapter(manifest: AdapterManifest, context: PluginContext) -> DemoAdapter:
    return DemoAdapter(manifest)
