from __future__ import annotations

from corretor.domain.entities import AdapterManifest, PluginContext, RawInstallment
from corretor.domain.errors import AdapterNotConfigured


class TemplateAdapter:
    manifest: AdapterManifest

    def __init__(self, manifest: AdapterManifest, context: PluginContext) -> None:
        self.manifest = manifest
        self.context = context

    def fetch_pending(self) -> list[RawInstallment]:
        # TODO: consultar o portal/API e retornar um snapshot COMPLETO.
        # Em falha/parse parcial, levantar AdapterError.
        raise AdapterNotConfigured("plugin de exemplo ainda não implementado")
