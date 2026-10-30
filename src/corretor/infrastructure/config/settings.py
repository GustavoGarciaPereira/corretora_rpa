from __future__ import annotations

import os
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Corretor RPA"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'corretor.db'}"
    evidence_dir: Path = BASE_DIR / "data" / "evidence"

    enable_scheduler: bool = False
    scheduler_hour: int = 8
    scheduler_minute: int = 0
    timezone: str = "America/Sao_Paulo"
    stale_after_hours: int = 26
    seed_demo: bool = False
    plugin_paths: str = ""

    bradesco_state_path: Path = BASE_DIR / "data" / "sessions" / "bradesco.json"
    bradesco_endpoint: str = (
        "https://wwwn.bradescoseguros.com.br/pnegocios/wps/"
        "PA_BSPN-DBoardAuto-PU/api/parcelas/v1/list"
    )
    bradesco_proposals_endpoint: str = (
        "https://wwwn.bradescoseguros.com.br/pnegocios/wps/"
        "PA_BSPN-DBoardAuto-PU/api/propostas/pendentes/v1/view"
    )
    bradesco_collect_parcelas: bool = False
    bradesco_collect_proposals: bool = True
    bradesco_headless: bool = True
    bradesco_timeout_ms: int = 60_000

    # API oficial (OAuth2 client credentials + mTLS opcional)
    bradesco_mode: str = "auto"  # auto | api | html
    bradesco_api_base_url: str = (
        "https://sauto.bradescoseguros.com.br/V2/WSBL-GerenciaCarteiraCsp/service"
    )
    bradesco_api_token_url: str = "https://sauto.bradescoseguros.com.br/V2/Auth"
    bradesco_api_client_id: str = ""
    bradesco_api_client_secret: SecretStr | None = None
    bradesco_api_secret_source: str = "env"  # env | keyring
    bradesco_api_keyring_service: str = "corretor-rpa"
    bradesco_api_keyring_username: str = "bradesco-api"
    bradesco_api_cnpj_provedor: str = ""
    bradesco_api_cpf_cnpj_corretor: str = ""
    bradesco_api_scope: str = "web"
    bradesco_api_feature_toggle: str = "0"
    bradesco_api_token_extra: str = ""
    bradesco_api_cert_path: Path | None = None
    bradesco_api_key_path: Path | None = None
    bradesco_api_ca_bundle: Path | None = None
    bradesco_api_verify_tls: bool = True
    bradesco_api_timeout_ms: int = 60_000

    @property
    def plugin_path_list(self) -> list[Path]:
        if not self.plugin_paths.strip():
            return []
        return [
            Path(part).expanduser() for part in self.plugin_paths.split(os.pathsep) if part.strip()
        ]

    @property
    def bradesco_context(self) -> dict[str, object]:
        return {
            "bradesco_state_path": str(self.bradesco_state_path),
            "bradesco_endpoint": self.bradesco_endpoint,
            "bradesco_proposals_endpoint": self.bradesco_proposals_endpoint,
            "bradesco_collect_parcelas": self.bradesco_collect_parcelas,
            "bradesco_collect_proposals": self.bradesco_collect_proposals,
            "bradesco_headless": self.bradesco_headless,
            "bradesco_timeout_ms": self.bradesco_timeout_ms,
            "bradesco_mode": self.bradesco_mode,
            "bradesco_api_base_url": self.bradesco_api_base_url,
            "bradesco_api_token_url": self.bradesco_api_token_url,
            "bradesco_api_client_id": self.bradesco_api_client_id,
            "bradesco_api_client_secret": self.bradesco_api_client_secret,
            "bradesco_api_secret_source": self.bradesco_api_secret_source,
            "bradesco_api_keyring_service": self.bradesco_api_keyring_service,
            "bradesco_api_keyring_username": self.bradesco_api_keyring_username,
            "bradesco_api_cnpj_provedor": self.bradesco_api_cnpj_provedor,
            "bradesco_api_cpf_cnpj_corretor": self.bradesco_api_cpf_cnpj_corretor,
            "bradesco_api_scope": self.bradesco_api_scope,
            "bradesco_api_feature_toggle": self.bradesco_api_feature_toggle,
            "bradesco_api_token_extra": self.bradesco_api_token_extra,
            "bradesco_api_cert_path": (
                str(self.bradesco_api_cert_path) if self.bradesco_api_cert_path else ""
            ),
            "bradesco_api_key_path": (
                str(self.bradesco_api_key_path) if self.bradesco_api_key_path else ""
            ),
            "bradesco_api_ca_bundle": (
                str(self.bradesco_api_ca_bundle) if self.bradesco_api_ca_bundle else ""
            ),
            "bradesco_api_verify_tls": self.bradesco_api_verify_tls,
            "bradesco_api_timeout_ms": self.bradesco_api_timeout_ms,
        }
