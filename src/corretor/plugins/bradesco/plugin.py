from __future__ import annotations

from corretor.domain.entities import AdapterManifest, PluginContext
from corretor.domain.ports import InsurerAdapter

from .adapter import BradescoAdapter
from .api_adapter import BradescoApiAdapter


def _has_api_config(context: PluginContext) -> bool:
    client_id = str(context.get("bradesco_api_client_id", "")).strip()
    cnpj = str(context.get("bradesco_api_cnpj_provedor", "")).strip()
    cpf = str(context.get("bradesco_api_cpf_cnpj_corretor", "")).strip()
    secret_source = str(context.get("bradesco_api_secret_source", "env")).strip()
    secret = context.get("bradesco_api_client_secret")
    has_secret = bool(secret) or secret_source == "keyring"
    return bool(client_id and cnpj and cpf and has_secret)


def create_adapter(manifest: AdapterManifest, context: PluginContext) -> InsurerAdapter:
    mode = str(context.get("bradesco_mode", "auto")).strip().lower()
    if mode == "api" or (mode == "auto" and _has_api_config(context)):
        return BradescoApiAdapter(manifest, context)
    return BradescoAdapter(manifest, context)
