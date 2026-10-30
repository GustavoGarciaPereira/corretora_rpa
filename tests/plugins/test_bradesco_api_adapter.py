from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from corretor.domain.entities import AdapterManifest, PluginContext
from corretor.domain.errors import AdapterError, AdapterNotConfigured
from corretor.plugins.bradesco.api_adapter import BradescoApiAdapter


def manifest() -> AdapterManifest:
    return AdapterManifest(
        slug="bradesco",
        name="Bradesco Seguros",
        version="0.1.0",
        status="discovery",
    )


def context(**overrides) -> PluginContext:
    settings = {
        "bradesco_api_base_url": "https://api.example/V2/WSBL-GerenciaCarteiraCsp/service",
        "bradesco_api_token_url": "https://api.example/V2/Auth",
        "bradesco_api_client_id": "client-id",
        "bradesco_api_client_secret": SecretStr("client-secret"),
        "bradesco_api_cnpj_provedor": "12345678000195",
        "bradesco_api_cpf_cnpj_corretor": "12345678901",
    }
    settings.update(overrides)
    return PluginContext(settings=settings)


def proposal_payload() -> dict:
    return {
        "propostas": [
            {
                "proponente": {"nome": "Cliente Fictício"},
                "sucursal": "637",
                "agencia": "0000",
                "numProposta": "637077119",
                "tpProposta": "Renovação",
                "vencimento": {
                    "status": "Processando nova chance",
                    "dtVencimento": "29/10/2026",
                    "formaPagamento": "Boleto",
                },
            }
        ]
    }


def test_cliente_oauth_e_endpoint_pendentes() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.url.path.endswith("/V2/Auth/"):
            body = request.content.decode()
            assert "grant_type=client_credentials" in body
            assert "client_id=client-id" in body
            return httpx.Response(
                200,
                json={
                    "access_token": "token-123",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        if request.url.path.endswith("/pendentes"):
            assert request.headers["authorization"] == "Bearer token-123"
            body = json.loads(request.content)
            dto = body["propostasPendentesRequestDTO"]
            assert dto["cnpjProvedor"] == "12345678000195"
            assert dto["cpfCnpjCorretor"] == "12345678901"
            return httpx.Response(200, json=proposal_payload())
        return httpx.Response(404)

    adapter = BradescoApiAdapter(manifest(), context(), transport=httpx.MockTransport(handler))
    items = adapter.fetch_pending()

    assert len(items) == 1
    assert items[0].policy_number == "637-0000/637077119"
    assert calls[0].endswith("/V2/Auth/")
    assert calls[1].endswith("/pendentes")


def test_credenciais_rejeitadas_falham() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid_client"})

    adapter = BradescoApiAdapter(manifest(), context(), transport=httpx.MockTransport(handler))
    with pytest.raises(AdapterError, match="credenciais"):
        adapter.fetch_pending()


def test_configuracao_incompleta_falha() -> None:
    adapter = BradescoApiAdapter(
        manifest(),
        context(bradesco_api_client_id=""),
        transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )
    with pytest.raises(AdapterNotConfigured, match="CLIENT_ID"):
        adapter.fetch_pending()
