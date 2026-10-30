#!/usr/bin/env python3
"""Tentativa de login automático no portal do Bradesco.

Usa credenciais do keyring/Vault (nunca argumentos de linha de comando).
Se o portal exigir reCAPTCHA/MFA, encerra com status `captcha` e não tenta
contornar. O login manual continua disponível em `/sessions`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

from corretor.infrastructure.config import Settings
from corretor.infrastructure.credentials import (
    CredentialsError,
    resolve_bradesco_credentials,
)


def write_result(
    result_path: Path,
    status: str,
    message: str,
    started_at: datetime,
) -> None:
    result_path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "status": status,
        "message": message,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
    }
    temporary = result_path.with_suffix(result_path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, result_path)


async def _captcha_visible(page) -> bool:
    challenge = page.locator("iframe[src*='recaptcha/api2/bframe']")
    if await challenge.count() and await challenge.first.is_visible():
        return True
    try:
        text = (await page.locator("body").inner_text()).lower()
    except Exception:  # noqa: BLE001
        return False
    return "faça o desafio" in text or "verifique se você é humano" in text


async def _credential_error(page) -> bool:
    messages = page.locator("[data-message][data-show='true']")
    if not await messages.count():
        return False
    text = " ".join(await messages.all_inner_texts()).lower()
    return any(term in text for term in ("inválid", "incorret", "não confere", "não encontrad"))


async def auto_login(args: argparse.Namespace) -> int:
    started_at = datetime.now(UTC)
    result_path = Path(args.result).expanduser()
    state_path = Path(args.state).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)

    settings = Settings()
    try:
        credentials = resolve_bradesco_credentials(settings)
    except CredentialsError as exc:
        write_result(result_path, "credentials", str(exc), started_at)
        return 2

    headless = settings.bradesco_auto_login_headless
    try:
        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch(headless=headless, channel="chrome")
            except Exception:  # noqa: BLE001 - fallback para Chromium
                browser = await playwright.chromium.launch(headless=headless)

            context_kwargs = {
                "locale": "pt-BR",
                "timezone_id": "America/Sao_Paulo",
                "viewport": {"width": 1440, "height": 900},
            }
            if state_path.exists():
                context_kwargs["storage_state"] = str(state_path)
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            try:
                await page.goto(args.url, wait_until="domcontentloaded", timeout=60_000)
                await page.wait_for_timeout(1500)

                reject = page.locator("#adopt-reject-all-button")
                if await reject.count() and await reject.is_visible():
                    await reject.click()
                    await page.wait_for_timeout(500)

                # Corretor é o perfil padrão; garante a seleção se necessário.
                try:
                    if not await page.locator("#corretor-login").is_checked():
                        await page.locator(".tag_Home_Login_Corretor").click()
                except Exception:  # noqa: BLE001
                    pass

                await page.fill("#CpfCnpjTelaInicial", credentials.user)
                continue_button = page.locator("#tag_Home_Login-Continuar")
                if await continue_button.count() and await continue_button.is_visible():
                    await continue_button.click()
                await page.wait_for_selector("#senha", state="visible", timeout=20_000)
                await page.fill("#senha", credentials.password)
                await page.click("#tag_Home_Login-entrar")

                deadline = time.monotonic() + args.timeout
                while time.monotonic() < deadline:
                    if "arealogada" in page.url.lower():
                        temporary = state_path.with_suffix(state_path.suffix + ".tmp")
                        await context.storage_state(path=str(temporary))
                        os.replace(temporary, state_path)
                        write_result(
                            result_path,
                            "success",
                            "login automático concluído; sessão salva",
                            started_at,
                        )
                        return 0
                    if await _captcha_visible(page):
                        write_result(
                            result_path,
                            "captcha",
                            "o portal exigiu captcha/MFA; renove manualmente",
                            started_at,
                        )
                        return 3
                    if await _credential_error(page):
                        write_result(
                            result_path,
                            "credentials",
                            "credenciais rejeitadas pelo portal; verifique o cofre",
                            started_at,
                        )
                        return 4
                    await page.wait_for_timeout(1000)

                write_result(
                    result_path,
                    "error",
                    "tempo esgotado aguardando o login automático",
                    started_at,
                )
                return 5
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:  # noqa: BLE001
        write_result(
            result_path,
            "error",
            f"falha no login automático ({exc.__class__.__name__})",
            started_at,
        )
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Login automático Bradesco")
    parser.add_argument("--state", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    return parser


if __name__ == "__main__":
    raise SystemExit(asyncio.run(auto_login(build_parser().parse_args())))
