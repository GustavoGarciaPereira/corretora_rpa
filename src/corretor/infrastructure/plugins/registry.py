from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

import yaml

from corretor.domain.entities import AdapterManifest, PluginContext
from corretor.domain.errors import PluginError
from corretor.domain.ports import InsurerAdapter

from .loaded_plugin import LoadedPlugin
from .plugin_load_error import PluginLoadError

logger = logging.getLogger(__name__)


class PluginRegistry:
    def __init__(
        self,
        plugin_dirs: list[Path],
        context: PluginContext | None = None,
    ) -> None:
        self.plugin_dirs = [Path(path) for path in plugin_dirs]
        self.context = context or PluginContext()
        self._plugins: dict[str, LoadedPlugin] = {}
        self._errors: list[PluginLoadError] = []
        self.discover()

    def discover(self) -> None:
        self._plugins.clear()
        self._errors.clear()
        for root in self.plugin_dirs:
            if not root.exists():
                continue
            for child in sorted(root.iterdir()):
                if child.is_dir() and not child.name.startswith("_"):
                    self._load_dir(child)

    def _load_dir(self, path: Path) -> None:
        manifest_path = path / "manifest.yaml"
        plugin_path = path / "plugin.py"
        if not manifest_path.exists() or not plugin_path.exists():
            self._errors.append(PluginLoadError(str(path), "manifest.yaml ou plugin.py ausente"))
            return
        try:
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                raise PluginError("manifest.yaml deve ser um mapa")
            if "capabilities" in data:
                data["capabilities"] = tuple(data["capabilities"])
            manifest = AdapterManifest(**data)

            module_name = f"_corretor_plugin_{manifest.slug}_{abs(hash(path.resolve()))}"
            spec = importlib.util.spec_from_file_location(
                module_name,
                plugin_path,
                submodule_search_locations=[str(path)],
            )
            if spec is None or spec.loader is None:
                raise PluginError("não foi possível carregar plugin.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            factory = getattr(module, "create_adapter", None)
            if not callable(factory):
                raise PluginError("plugin.py não expõe create_adapter(manifest, context)")

            adapter = factory(manifest, self.context)
            if not hasattr(adapter, "fetch_pending") or not callable(adapter.fetch_pending):
                raise PluginError("adapter não implementa fetch_pending()")

            if manifest.slug in self._plugins:
                raise PluginError(f"slug duplicado: {manifest.slug}")
            self._plugins[manifest.slug] = LoadedPlugin(
                manifest=manifest,
                factory=factory,
                source=str(path),
            )
        except Exception as exc:  # noqa: BLE001 - plugin quebrado não derruba a plataforma
            logger.exception("falha ao carregar plugin em %s", path)
            self._errors.append(PluginLoadError(str(path), str(exc)))

    def get(self, slug: str) -> InsurerAdapter:
        plugin = self._plugins.get(slug)
        if plugin is None:
            raise PluginError(f"plugin não encontrado: {slug}")
        return plugin.factory(plugin.manifest, self.context)

    def has(self, slug: str) -> bool:
        return slug in self._plugins

    def manifests(self) -> list[AdapterManifest]:
        return sorted(
            (plugin.manifest for plugin in self._plugins.values()),
            key=lambda manifest: manifest.name,
        )

    @property
    def errors(self) -> list[PluginLoadError]:
        return list(self._errors)
