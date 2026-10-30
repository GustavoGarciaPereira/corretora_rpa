from __future__ import annotations

import os
from pathlib import Path

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
    bradesco_collect_proposals: bool = True
    bradesco_headless: bool = True
    bradesco_timeout_ms: int = 60_000

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
            "bradesco_collect_proposals": self.bradesco_collect_proposals,
            "bradesco_headless": self.bradesco_headless,
            "bradesco_timeout_ms": self.bradesco_timeout_ms,
        }
