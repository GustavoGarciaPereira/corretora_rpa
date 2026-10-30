from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import httpx
from pydantic import SecretStr

from corretor.domain.entities import AdapterManifest, PluginContext, RawInstallment
from corretor.domain.errors import AdapterError, AdapterNotConfigured

from .api_mapping import map_api_payload

logger = logging.getLogger(__name__)


class BradescoApiAdapter:
    """Adapter oficial: OAuth2 client credentials + POST /pendentes."""

    manifest: AdapterManifest

    def __init__(
        self,
        manifest: AdapterManifest,
        context: PluginContext,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.manifest = manifest
        self.base_url = str(context.get("bradesco_api_base_url", "")).strip().rstrip("/")
        self.token_url = str(context.get("bradesco_api_token_url", "")).strip().rstrip("/")
        self.client_id = str(context.get("bradesco_api_client_id", "")).strip()
        self.client_secret = context.get("bradesco_api_client_secret")
        self.secret_source = str(context.get("bradesco_api_secret_source", "env")).strip()
        self.keyring_service = str(context.get("bradesco_api_keyring_service", "corretor-rpa"))
        self.keyring_username = str(context.get("bradesco_api_keyring_username", "bradesco-api"))
        self.cnpj_provedor = str(context.get("bradesco_api_cnpj_provedor", "")).strip()
        self.cpf_cnpj_corretor = str(context.get("bradesco_api_cpf_cnpj_corretor", "")).strip()
        self.scope = str(context.get("bradesco_api_scope", "web")).strip() or "web"
        self.feature_toggle = str(context.get("bradesco_api_feature_toggle", "0")).strip()
        self.token_extra = str(context.get("bradesco_api_token_extra", "")).strip()
        self.cert_path = str(context.get("bradesco_api_cert_path", "")).strip()
        self.key_path = str(context.get("bradesco_api_key_path", "")).strip()
        self.ca_bundle = str(context.get("bradesco_api_ca_bundle", "")).strip()
        self.verify_tls = bool(context.get("bradesco_api_verify_tls", True))
        self.timeout_s = int(context.get("bradesco_api_timeout_ms", 60_000)) / 1000
        self._transport = transport
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def _resolve_secret(self) -> str:
        if self.secret_source == "keyring":
            try:
                import keyring
            except ImportError as exc:
                raise AdapterNotConfigured(
                    "keyring não instalado; instale o extra 'vault'"
                ) from exc
            secret = keyring.get_password(self.keyring_service, self.keyring_username)
            if not secret:
                raise AdapterNotConfigured(
                    "segredo da API não encontrado no keyring "
                    f"({self.keyring_service}/{self.keyring_username})"
                )
            return secret

        secret: Any = self.client_secret
        if isinstance(secret, SecretStr):
            secret = secret.get_secret_value()
        if not secret:
            raise AdapterNotConfigured(
                "BRADESCO_API_CLIENT_SECRET não configurado "
                "(ou use BRADESCO_API_SECRET_SOURCE=keyring)"
            )
        return str(secret)

    def _validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("BRADESCO_API_BASE_URL", self.base_url),
                ("BRADESCO_API_TOKEN_URL", self.token_url),
                ("BRADESCO_API_CLIENT_ID", self.client_id),
                ("BRADESCO_API_CNPJ_PROVEDOR", self.cnpj_provedor),
                ("BRADESCO_API_CPF_CNPJ_CORRETOR", self.cpf_cnpj_corretor),
            )
            if not value
        ]
        if missing:
            raise AdapterNotConfigured(
                "configuração da API Bradesco incompleta: " + ", ".join(missing)
            )

    def _client(self) -> httpx.Client:
        cert: str | tuple[str, str] | None = None
        if self.cert_path:
            cert_file = Path(self.cert_path).expanduser()
            if not cert_file.exists():
                raise AdapterNotConfigured(f"certificado da API não encontrado: {cert_file}")
            if self.key_path:
                key_file = Path(self.key_path).expanduser()
                if not key_file.exists():
                    raise AdapterNotConfigured(f"chave do certificado não encontrada: {key_file}")
                cert = (str(cert_file), str(key_file))
            else:
                cert = str(cert_file)

        verify: bool | str = self.verify_tls
        if self.ca_bundle:
            ca_file = Path(self.ca_bundle).expanduser()
            if not ca_file.exists():
                raise AdapterNotConfigured(f"CA bundle não encontrado: {ca_file}")
            verify = str(ca_file)

        return httpx.Client(
            timeout=httpx.Timeout(self.timeout_s),
            cert=cert,
            verify=verify,
            transport=self._transport,
        )

    def _get_token(self, client: httpx.Client) -> str:
        now = time.monotonic()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        data = {
            "grant_type": "client_credentials",
            "scope": self.scope,
            "client_id": self.client_id,
            "client_secret": self._resolve_secret(),
        }
        if self.token_extra:
            data["token"] = self.token_extra

        response = client.post(
            f"{self.token_url}/",
            data=data,
            headers={"Accept": "application/json"},
        )
        if response.status_code in (400, 401, 403):
            raise AdapterError("credenciais da API Bradesco rejeitadas")
        if response.status_code >= 400:
            raise AdapterError(f"falha ao obter token da API Bradesco: HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AdapterError("resposta de token da API Bradesco inválida") from exc

        token = payload.get("access_token")
        if not token:
            raise AdapterError("API Bradesco não retornou access_token")
        expires_in = int(payload.get("expires_in", 3600))
        self._access_token = str(token)
        self._token_expires_at = now + max(60, expires_in - 60)
        return self._access_token

    def _post_pendentes(self, client: httpx.Client, token: str) -> httpx.Response:
        body: dict[str, Any] = {
            "cnpjProvedor": self.cnpj_provedor,
            "cpfCnpjCorretor": self.cpf_cnpj_corretor,
        }
        if self.feature_toggle:
            body["featureToggle"] = self.feature_toggle
        return client.post(
            f"{self.base_url}/pendentes",
            json={"propostasPendentesRequestDTO": body},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )

    def fetch_pending(self) -> list[RawInstallment]:
        self._validate()

        try:
            with self._client() as client:
                token = self._get_token(client)
                response = self._post_pendentes(client, token)
                if response.status_code in (401, 403):
                    # token pode ter expirado entre o cache e a chamada
                    self._access_token = None
                    token = self._get_token(client)
                    response = self._post_pendentes(client, token)
                if response.status_code >= 400:
                    detail = " ".join(response.text.split())[:200]
                    raise AdapterError(
                        f"API Bradesco respondeu HTTP {response.status_code}"
                        + (f": {detail}" if detail else "")
                    )
                payload = response.json()
        except (AdapterError, AdapterNotConfigured):
            raise
        except httpx.HTTPError as exc:
            logger.exception("falha de HTTP na API Bradesco")
            raise AdapterError(
                f"falha de comunicação com a API Bradesco: {exc.__class__.__name__}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            logger.exception("falha inesperada na API Bradesco")
            raise AdapterError(
                f"falha inesperada na API Bradesco: {exc.__class__.__name__}"
            ) from exc

        return map_api_payload(payload)


__all__ = ["BradescoApiAdapter"]
