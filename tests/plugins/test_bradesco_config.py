from __future__ import annotations

import pytest

from corretor.domain.entities import AdapterManifest, PluginContext
from corretor.domain.errors import AdapterNotConfigured
from corretor.plugins.bradesco.adapter import BradescoAdapter


def manifest() -> AdapterManifest:
    return AdapterManifest(
        slug="bradesco",
        name="Bradesco Seguros",
        version="0.1.0",
        status="discovery",
        requires_session=True,
    )


def test_por_padrao_coleta_somente_propostas() -> None:
    adapter = BradescoAdapter(manifest(), PluginContext(settings={}))
    assert adapter.collect_parcelas is False
    assert adapter.collect_proposals is True


def test_sem_parcelas_e_sem_propostas_falha_explicitamente() -> None:
    adapter = BradescoAdapter(
        manifest(),
        PluginContext(settings={"bradesco_collect_proposals": False}),
    )
    with pytest.raises(AdapterNotConfigured, match="desativada"):
        adapter.fetch_pending()
