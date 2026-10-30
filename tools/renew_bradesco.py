#!/usr/bin/env python3
"""Renovação assistida da sessão do Bradesco.

Abre o navegador visível, espera o login manual e salva o `storage_state`
automaticamente quando a área logada aparecer. O reCAPTCHA/MFA é resolvido
pelo operador; o script não lê, não pede e não grava senha.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright


def write_result(
    result_path: Path,
    status: str,
    message: str,
    started_at: datetime,
    **extra,
) -> None:
    result_path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "status": status,
        "message": message,
        "started_at": started_at.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        **extra,
    }
    temporary = result_path.with_suffix(result_path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, result_path)


async def renew(args: argparse.Namespace) -> int:
    started_at = datetime.now(UTC)
    result_path = Path(args.result).expanduser()
    deterministic_error = None
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        deterministic_error = (
            "DISPLAY não configurado; execute a renovação na máquina do operador "
            "ou use um navegador remoto (noVNC)."
        )
    if deterministic_error:
        write_result(result_path, "error", deterministic_error, started_at)
        return 2

    state_path = Path(args.state).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch(headless=False, channel="chrome")
            except Exception:  # noqa: BLE001 - fallback para Chromium
                browser = await playwright.chromium.launch(headless=False)

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
                deadline = time.monotonic() + args.timeout
                logged_in = "arealogada" in page.url.lower()
                while not logged_in and time.monotonic() < deadline:
                    await page.wait_for_timeout(1000)
                    logged_in = "arealogada" in page.url.lower()

                if not logged_in:
                    write_result(
                        result_path,
                        "error",
                        "tempo esgotado aguardando o login manual",
                        started_at,
                    )
                    return 3

                temporary = state_path.with_suffix(state_path.suffix + ".tmp")
                await context.storage_state(path=str(temporary))
                os.replace(temporary, state_path)
                write_result(
                    result_path,
                    "success",
                    "sessão renovada e salva automaticamente",
                    started_at,
                    state_path=str(state_path),
                )
                return 0
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:  # noqa: BLE001
        write_result(
            result_path,
            "error",
            f"falha ao renovar a sessão ({exc.__class__.__name__}); tente novamente",
            started_at,
        )
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Renovação assistida Bradesco")
    parser.add_argument("--state", required=True, help="caminho do storage_state.json")
    parser.add_argument("--result", required=True, help="arquivo de resultado JSON")
    parser.add_argument("--url", required=True, help="URL de login do portal")
    parser.add_argument(
        "--timeout", type=int, default=600, help="tempo máximo de espera em segundos"
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(asyncio.run(renew(build_parser().parse_args())))
