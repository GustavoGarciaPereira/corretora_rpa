from __future__ import annotations

import pytest
from pydantic import SecretStr

from corretor.domain.entities import AdapterManifest, PluginContext
from corretor.domain.errors import AdapterNotConfigured, AdapterSessionExpired
from corretor.plugins.bradesco.adapter import BradescoAdapter
from corretor.plugins.bradesco.api_adapter import BradescoApiAdapter
from corretor.plugins.bradesco.plugin import create_adapter


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


def test_sem_sessao_salva_falha_como_expirada(tmp_path) -> None:
    adapter = BradescoAdapter(
        manifest(),
        PluginContext(
            settings={
                "bradesco_proposals_endpoint": "https://example.invalid/propostas",
                "bradesco_state_path": str(tmp_path / "ausente.json"),
            }
        ),
    )
    with pytest.raises(AdapterSessionExpired, match="não encontrada"):
        adapter.fetch_pending()


def test_modo_api_usa_adapter_oficial() -> None:
    adapter = create_adapter(
        manifest(),
        PluginContext(
            settings={
                "bradesco_mode": "api",
                "bradesco_api_client_id": "client",
                "bradesco_api_client_secret": SecretStr("secret"),
                "bradesco_api_cnpj_provedor": "12345678000195",
                "bradesco_api_cpf_cnpj_corretor": "12345678901",
            }
        ),
    )
    assert isinstance(adapter, BradescoApiAdapter)


def test_modo_html_forca_fallback() -> None:
    adapter = create_adapter(
        manifest(),
        PluginContext(settings={"bradesco_mode": "html"}),
    )
    assert isinstance(adapter, BradescoAdapter)
