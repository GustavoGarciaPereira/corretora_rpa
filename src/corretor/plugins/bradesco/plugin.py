from __future__ import annotations

from corretor.domain.entities import AdapterManifest, PluginContext

from .adapter import BradescoAdapter


def create_adapter(manifest: AdapterManifest, context: PluginContext) -> BradescoAdapter:
    return BradescoAdapter(manifest, context)
