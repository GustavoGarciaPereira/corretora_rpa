from __future__ import annotations

from corretor.domain.entities import AdapterManifest, PluginContext

from .adapter import TemplateAdapter


def create_adapter(manifest: AdapterManifest, context: PluginContext) -> TemplateAdapter:
    return TemplateAdapter(manifest, context)
