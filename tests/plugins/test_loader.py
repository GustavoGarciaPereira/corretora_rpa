from __future__ import annotations

from pathlib import Path

import corretor.plugins
from corretor.infrastructure.plugins import PluginRegistry


def builtin_root() -> Path:
    return Path(corretor.plugins.__file__).resolve().parent


def test_descobre_demo_e_bradesco_e_ignora_template() -> None:
    registry = PluginRegistry([builtin_root()])
    slugs = {manifest.slug for manifest in registry.manifests()}
    assert {"demo", "bradesco"} <= slugs
    assert "template" not in slugs
    assert registry.errors == []

    adapter = registry.get("demo")
    assert len(adapter.fetch_pending()) == 5


def test_plugin_quebrado_nao_derruba_os_demais(tmp_path) -> None:
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "manifest.yaml").write_text(
        "\n".join(
            [
                "slug: broken",
                "name: Plugin Quebrado",
                "version: 0.1.0",
                "mode: python",
                "status: discovery",
                "capabilities:",
                "  - read_only",
            ]
        ),
        encoding="utf-8",
    )
    (broken / "plugin.py").write_text("raise RuntimeError('boom no plugin')\n", encoding="utf-8")

    registry = PluginRegistry([builtin_root(), tmp_path])
    slugs = {manifest.slug for manifest in registry.manifests()}
    assert "demo" in slugs
    assert "broken" not in slugs
    assert any("boom no plugin" in error.error for error in registry.errors)
