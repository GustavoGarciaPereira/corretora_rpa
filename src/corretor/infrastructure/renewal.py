from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .config import Settings
from .credentials import credentials_available

PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class RenewalStatus:
    status: str  # idle | running | success | error | captcha | credentials | disabled
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pid: int | None = None


class RenewalError(RuntimeError):
    pass


class SessionRenewalManager:
    """Orquestra o processo de renovação assistida da sessão do Bradesco."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.result_path = settings.bradesco_state_path.parent / "bradesco-renewal.json"
        self._process: subprocess.Popen | None = None

    def _write(
        self,
        status: str,
        message: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        pid: int | None = None,
    ) -> RenewalStatus:
        now = datetime.now(UTC)
        document = {
            "status": status,
            "message": message,
            "started_at": (started_at or now).isoformat(),
            "finished_at": (finished_at or now).isoformat(),
        }
        if pid is not None:
            document["pid"] = pid
        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.result_path.with_suffix(self.result_path.suffix + ".tmp")
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.result_path)
        return RenewalStatus(
            status=status,
            message=message,
            started_at=started_at or now,
            finished_at=finished_at,
            pid=pid,
        )

    def _read(self) -> RenewalStatus | None:
        if not self.result_path.exists():
            return None
        try:
            data = json.loads(self.result_path.read_text(encoding="utf-8"))
            return RenewalStatus(
                status=str(data.get("status", "error")),
                message=str(data.get("message", "")),
                started_at=(
                    datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
                ),
                finished_at=(
                    datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None
                ),
                pid=int(data["pid"]) if data.get("pid") else None,
            )
        except (OSError, ValueError):
            return RenewalStatus("error", "resultado da renovação inválido")

    def status(self) -> RenewalStatus:
        if not self.settings.session_renewal_enabled:
            return RenewalStatus(
                "disabled",
                "renovação automática desabilitada; use o comando manual",
            )

        result = self._read()
        if result is not None and result.status in {
            "success",
            "error",
            "captcha",
            "credentials",
        }:
            return result

        if self._process is not None:
            if self._process.poll() is None:
                return RenewalStatus(
                    "running",
                    "navegador aberto; faça o login manual no portal",
                    pid=self._process.pid,
                )
            if result is None:
                return RenewalStatus("error", "o processo de renovação encerrou sem resultado")

        if result is not None:
            if result.status == "running":
                if result.pid is not None:
                    if self._pid_alive(result.pid):
                        return result
                    return RenewalStatus(
                        "error",
                        "o processo de renovação não está mais em execução; tente novamente",
                    )
                age = (
                    datetime.now(UTC) - result.started_at if result.started_at is not None else None
                )
                if age is not None and age.total_seconds() > 60:
                    return RenewalStatus("error", "renovação anterior expirou; tente novamente")
            return result

        return RenewalStatus("idle", "pronto para abrir o navegador")

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def auto_available(self) -> bool:
        return (
            self.settings.session_renewal_enabled
            and self.settings.bradesco_auto_login_enabled
            and credentials_available(self.settings)
        )

    def start(self, auto: bool = False) -> RenewalStatus:
        current = self.status()
        if current.status in {"disabled", "running"}:
            return current

        if auto:
            if not self.settings.bradesco_auto_login_enabled:
                return self._write(
                    "error",
                    "login automático desabilitado; use a renovação manual",
                )
            if not credentials_available(self.settings):
                return self._write(
                    "credentials",
                    "credenciais não configuradas; cadastre no cofre "
                    "(corretor credentials set bradesco)",
                )
            script = "auto_login_bradesco.py"
            message = (
                "tentando login automático em background; se houver captcha/MFA, renove manualmente"
            )
        else:
            script = "renew_bradesco.py"
            message = "abrindo navegador; faça o login manual no portal"

        self.result_path.parent.mkdir(parents=True, exist_ok=True)
        self.result_path.unlink(missing_ok=True)
        started_at = datetime.now(UTC)
        self._write("running", message, started_at=started_at)

        command = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / script),
            "--state",
            str(self.settings.bradesco_state_path),
            "--result",
            str(self.result_path),
            "--url",
            self.settings.bradesco_login_url,
            "--timeout",
            str(
                self.settings.bradesco_auto_login_timeout_s
                if auto
                else self.settings.session_renewal_timeout_s
            ),
        ]
        try:
            self._process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                env=os.environ.copy(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            return self._write(
                "error",
                f"não foi possível abrir o navegador ({exc.__class__.__name__})",
                started_at=started_at,
            )

        # Se o worker ainda não terminou, registra o PID para detectar processo
        # órfão após reload/restart do servidor.
        current = self._read()
        if current is not None and current.status == "running":
            self._write(
                "running",
                message,
                started_at=started_at,
                pid=self._process.pid,
            )
        return self.status()
