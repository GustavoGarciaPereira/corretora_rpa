#!/usr/bin/env python3
"""Descoberta assistida de um portal de seguradora.

Abre o portal em um navegador visível, registra a navegação e a rede enquanto
você faz o login MANUALMENTE. Nenhuma senha é solicitada, lida ou gravada.

Ao final, salva URL, prints, HTML, trace e sessão em `data/discovery/<slug>/`.
Esses arquivos podem conter dados pessoais/sessão e são ignorados pelo Git.

Uso:
    python tools/discover_portal.py --slug bradesco
    python tools/discover_portal.py --slug bradesco --url <url>
    python tools/discover_portal.py --slug teste --url https://example.com --headless --no-wait
"""

from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.async_api import Browser, BrowserContext, Page, Response, async_playwright

PORTALS = {
    "bradesco": ("https://wwwn.bradescoseguros.com.br/pnegocios2/wps/portal/portaldenegociosnovo/"),
    "allianz": "https://www.allianznet.com.br/ngx-azb-epac/public/home",
}

SENSITIVE_QUERY_KEYS = ("token", "session", "auth", "code", "password", "senha", "key")


def _safe_url(url: str) -> str:
    """Remove valores de query strings potencialmente sensíveis."""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    safe_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if any(sensitive in key.lower() for sensitive in SENSITIVE_QUERY_KEYS):
            value = "<redacted>"
        safe_pairs.append((key, value))
    return urlunparse(parsed._replace(query=urlencode(safe_pairs)))


def _write_json(path: Path, data: object) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


async def _open_browser(playwright, channel: str, headless: bool) -> tuple[Browser, str]:
    """Abre o Chrome do sistema; se falhar, tenta o Chromium do Playwright."""
    if channel:
        try:
            browser = await playwright.chromium.launch(headless=headless, channel=channel)
            return browser, channel
        except Exception as exc:  # noqa: BLE001 - fallback intencional
            print(f"[aviso] não foi possível abrir o canal '{channel}': {exc}")
            print("[aviso] tentando o Chromium instalado pelo Playwright...")
    browser = await playwright.chromium.launch(headless=headless)
    return browser, "chromium"


async def discover(args: argparse.Namespace) -> int:
    start_url = args.url or PORTALS.get(args.slug)
    if not start_url:
        print(
            f"[erro] URL não informada para '{args.slug}'. "
            f"Use --url ou um slug conhecido: {', '.join(sorted(PORTALS))}."
        )
        return 2
    if args.state and not Path(args.state).exists():
        print(f"[erro] storage_state não encontrado: {args.state}")
        return 2

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_root) / args.slug / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    network_path = output_dir / "network.jsonl"

    responses: list[dict[str, object]] = []
    navigations: list[dict[str, str]] = []

    def on_response(response: Response) -> None:
        request = response.request
        if request.resource_type not in {"xhr", "fetch", "document"}:
            return
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "method": request.method,
            "resource_type": request.resource_type,
            "url": _safe_url(response.url),
            "status": response.status,
            "content_type": response.headers.get("content-type", ""),
        }
        responses.append(entry)
        with network_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def on_navigation(frame) -> None:
        navigations.append(
            {
                "ts": datetime.now(UTC).isoformat(),
                "url": _safe_url(frame.url),
            }
        )

    async with async_playwright() as playwright:
        browser, channel_used = await _open_browser(playwright, args.channel, args.headless)
        context_kwargs: dict[str, object] = {
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
            "viewport": {"width": 1440, "height": 900},
        }
        if args.state:
            context_kwargs["storage_state"] = args.state
        context: BrowserContext = await browser.new_context(**context_kwargs)
        page: Page = await context.new_page()
        page.on("response", on_response)
        page.on("framenavigated", on_navigation)
        context.on("page", lambda popup: print(f"[nova aba] {_safe_url(popup.url)}"))

        await context.tracing.start(screenshots=True, snapshots=True, sources=False)

        print(f"\n[abrindo] {start_url}")
        print(f"[navegador] {channel_used} (headless={args.headless})")
        await page.goto(start_url, wait_until="domcontentloaded", timeout=args.timeout)

        if args.pause:
            if args.headless:
                print("[erro] --pause exige navegador visível (sem --headless).")
                await context.close()
                await browser.close()
                return 2
            print("\n" + "=" * 72)
            print("FAÇA O LOGIN MANUALMENTE NO NAVEGADOR.")
            print("Navegue até a tela desejada (ex.: Propostas Pendentes).")
            print("Depois, clique em RESUME na janela do Playwright Inspector.")
            print("Nenhuma senha é solicitada ou gravada por este script.")
            print("=" * 72 + "\n")
            await page.pause()
        elif not args.no_wait:
            print("\n" + "=" * 72)
            print("FAÇA O LOGIN MANUALMENTE NO NAVEGADOR.")
            print("Navegue até a tela de parcelas pendentes da seguradora.")
            print("Nenhuma senha é solicitada ou gravada por este script.")
            print("Quando estiver na tela desejada, volte aqui e pressione ENTER.")
            print("=" * 72 + "\n")
            await asyncio.to_thread(input, "Pressione ENTER para capturar... ")
        else:
            await page.wait_for_timeout(args.settle_ms)

        with suppress(Exception):
            await page.wait_for_load_state("networkidle", timeout=8000)
        await page.wait_for_timeout(args.settle_ms)

        final_url = _safe_url(page.url)
        title = await page.title()
        frames = [{"name": frame.name, "url": _safe_url(frame.url)} for frame in page.frames]

        try:
            await page.screenshot(path=str(output_dir / "page.png"), full_page=True)
        except Exception as exc:  # noqa: BLE001 - página muito longa/lenta
            print(f"[aviso] screenshot full-page falhou ({exc}); tentando viewport...")
            await page.screenshot(path=str(output_dir / "page.png"))

        (output_dir / "page.html").write_text(await page.content(), encoding="utf-8")
        await context.storage_state(path=str(output_dir / "state.json"))

        captcha_detected = any(
            "recaptcha" in frame["url"].lower() or "hcaptcha" in frame["url"].lower()
            for frame in frames
        )
        summary = {
            "slug": args.slug,
            "start_url": _safe_url(start_url),
            "final_url": final_url,
            "title": title,
            "captured_at": timestamp,
            "browser_channel": channel_used,
            "headless": args.headless,
            "captcha_detected": captcha_detected,
            "frames": frames,
            "navigations": navigations,
            "network_entries": len(responses),
            "output_dir": str(output_dir),
        }
        _write_json(output_dir / "summary.json", summary)

        try:
            await context.tracing.stop(path=str(output_dir / "trace.zip"))
        except Exception as exc:  # noqa: BLE001
            print(f"[aviso] não foi possível salvar o trace: {exc}")

        await context.close()
        await browser.close()

    print("\n" + "=" * 72)
    print("CAPTURA CONCLUÍDA")
    print(f"URL final : {summary['final_url']}")
    print(f"Título    : {summary['title']}")
    print(f"Frames    : {len(summary['frames'])}")
    print(f"Captcha   : {'sim' if summary['captcha_detected'] else 'não detectado'}")
    print(f"Rede      : {summary['network_entries']} entradas (XHR/fetch/document)")
    print(f"Pasta     : {output_dir}")
    print("Arquivos  : summary.json, network.jsonl, page.png, page.html, trace.zip, state.json")
    print("=" * 72)
    if summary["captcha_detected"]:
        print(
            "\n[aviso] captcha detectado no portal. O login deve ser manual; "
            "este script não contorna nem automatiza captcha."
        )
    print("\nAtenção: state.json e trace.zip podem conter sessão/PII.")
    print("A pasta data/ é ignorada pelo Git; não compartilhe esses arquivos.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Descoberta assistida de portal com Playwright (login manual)."
    )
    parser.add_argument("--slug", required=True, help="Nome curto, ex.: bradesco")
    parser.add_argument("--url", default=None, help="URL inicial do portal")
    parser.add_argument(
        "--state",
        default=None,
        help="Caminho de um storage_state.json para reutilizar a sessão",
    )
    parser.add_argument(
        "--channel",
        default="chrome",
        help="Canal do navegador (chrome, chromium ou vazio para o bundled)",
    )
    parser.add_argument(
        "--output-root",
        default="data/discovery",
        help="Diretório raiz das capturas (padrão: data/discovery)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Executa sem janela (não permite login manual)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Não espera ENTER; captura após o carregamento (útil para smoke test)",
    )
    parser.add_argument(
        "--pause",
        action="store_true",
        help="Abre o Playwright Inspector; use Resume para capturar",
    )
    parser.add_argument(
        "--settle-ms",
        type=int,
        default=1500,
        help="Espera extra após o carregamento, em milissegundos",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60_000,
        help="Timeout de navegação em milissegundos",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return asyncio.run(discover(args))
    except KeyboardInterrupt:
        print("\n[interrompido] nenhum dado foi enviado para fora da máquina.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
