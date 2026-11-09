from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from corretor.infrastructure import renewal as renewal_module
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


class FakeProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid

    def poll(self) -> None:
        return None


def _fake_popen(spawned: list[FakeProcess]):
    def start(*args, **kwargs):
        process = FakeProcess(pid=10_000 + len(spawned))
        spawned.append(process)
        return process

    return start


def _write_result(
    manager: SessionRenewalManager,
    status: str,
    *,
    finished_at: datetime | None = None,
) -> None:
    manager.result_path.parent.mkdir(parents=True, exist_ok=True)
    manager.result_path.write_text(
        json.dumps(
            {
                "status": status,
                "message": "tentativa anterior",
                "started_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                "finished_at": (finished_at or datetime.now(UTC)).isoformat(),
            }
        ),
        encoding="utf-8",
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


def test_forcar_expiracao_remove_sessao_e_resultado(tmp_path) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    manager.settings.bradesco_state_path.write_text("{}", encoding="utf-8")
    manager.result_path.write_text("{}", encoding="utf-8")

    assert manager.force_expire() is True
    assert not manager.settings.bradesco_state_path.exists()
    assert not manager.result_path.exists()
    assert manager.force_expire() is False


def test_start_nao_abre_dois_workers(tmp_path, monkeypatch) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    spawned: list[FakeProcess] = []
    monkeypatch.setattr(renewal_module.subprocess, "Popen", _fake_popen(spawned))
    monkeypatch.setattr(renewal_module, "credentials_available", lambda settings: True)

    first = manager.start(auto=True)
    second = manager.start(auto=True)

    assert first.status == "running"
    assert second.status == "running"
    assert len(spawned) == 1


def test_cooldown_evita_nova_tentativa_apos_falha(tmp_path, monkeypatch) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    _write_result(manager, "error")
    spawned: list[FakeProcess] = []
    monkeypatch.setattr(renewal_module.subprocess, "Popen", _fake_popen(spawned))
    monkeypatch.setattr(renewal_module, "credentials_available", lambda settings: True)

    status = manager.start(auto=True, respect_cooldown=True)

    assert status.status == "error"
    assert "tentativa anterior" in status.message
    assert spawned == []


def test_start_manual_ignora_cooldown(tmp_path, monkeypatch) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    _write_result(manager, "error")
    spawned: list[FakeProcess] = []
    monkeypatch.setattr(renewal_module.subprocess, "Popen", _fake_popen(spawned))
    monkeypatch.setattr(renewal_module, "credentials_available", lambda settings: True)

    status = manager.start(auto=True)

    assert status.status == "running"
    assert len(spawned) == 1


def test_cooldown_expira(tmp_path, monkeypatch) -> None:
    manager = SessionRenewalManager(settings(tmp_path))
    _write_result(
        manager,
        "error",
        finished_at=datetime.now(UTC)
        - timedelta(seconds=manager.settings.bradesco_auto_login_cooldown_s + 1),
    )
    spawned: list[FakeProcess] = []
    monkeypatch.setattr(renewal_module.subprocess, "Popen", _fake_popen(spawned))
    monkeypatch.setattr(renewal_module, "credentials_available", lambda settings: True)

    status = manager.start(auto=True, respect_cooldown=True)

    assert status.status == "running"
    assert len(spawned) == 1
