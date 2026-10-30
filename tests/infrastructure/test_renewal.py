from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from corretor.infrastructure.config import Settings
from corretor.infrastructure.renewal import SessionRenewalManager


def settings(tmp_path) -> Settings:
    return Settings(
        bradesco_state_path=tmp_path / "bradesco.json",
        session_renewal_enabled=True,
        bradesco_auto_login_enabled=True,
        bradesco_credential_source="env",
        bradesco_login_user="",
        bradesco_login_password=None,
    )


def test_login_automatico_sem_credenciais_nao_abre_navegador(tmp_path) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    status = manager.start(auto=True)
    assert status.status == "credentials"
    assert "credenciais" in status.message


def test_resultado_running_orfao_vira_erro(tmp_path) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    result = tmp_path / "bradesco-renewal.json"
    result.write_text(
        json.dumps(
            {
                "status": "running",
                "message": "antigo",
                "started_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                "finished_at": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    status = manager.status()
    assert status.status == "error"
    assert "expirou" in status.message
