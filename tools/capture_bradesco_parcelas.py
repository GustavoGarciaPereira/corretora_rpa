#!/usr/bin/env python3
"""Captura a lista de “Parcelas em Atraso” do Bradesco Auto.

Reutiliza um storage_state.json já autenticado, clica no card correto e salva
HTML, rede, screenshot, trace e corpos das chamadas de API relacionadas.

Uso:
    python tools/capture_bradesco_parcelas.py \
      --url "<url-da-area-auto>" \
      --state data/discovery/bradesco/<timestamp>/state.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from playwright.async_api import Response, async_playwright

SENSITIVE_QUERY_KEYS = ("token", "session", "auth", "code", "password", "senha", "key")
INTERESTING = ("/api/parcelas", "/api/apolices", "/api/propostas", "/api/sinistros")


def safe_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.query:
        return url
    pairs = [
        (k, "<redacted>" if any(s in k.lower() for s in SENSITIVE_QUERY_KEYS) else v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urlunparse(parsed._replace(query=urlencode(pairs)))


async def run(args: argparse.Namespace) -> int:
    if not Path(args.state).exists():
        print(f"[erro] state não encontrado: {args.state}")
        return 2

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = Path(args.output_root) / args.slug / stamp
    out.mkdir(parents=True, exist_ok=True)
    payloads = out / "payloads"
    payloads.mkdir(exist_ok=True)
    network_path = out / "network.jsonl"

    entries: list[dict[str, object]] = []
    interesting: list[tuple[int, Response]] = []

    def on_response(response: Response) -> None:
        req = response.request
        if req.resource_type not in {"xhr", "fetch", "document"}:
            return
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "method": req.method,
            "resource_type": req.resource_type,
            "url": safe_url(response.url),
            "status": response.status,
            "content_type": response.headers.get("content-type", ""),
        }
        entries.append(entry)
        with network_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if any(part in response.url for part in INTERESTING):
            interesting.append((len(entries) - 1, response))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=args.headless, channel="chrome")
        context = await browser.new_context(
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1440, "height": 900},
            storage_state=args.state,
        )
        page = await context.new_page()
        page.on("response", on_response)
        await context.tracing.start(screenshots=True, snapshots=True, sources=False)

        print(f"[abrindo] {args.url}")
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        if "login" in page.url.lower() or "portaldenegociosnovo" in page.url.lower():
            print("[erro] a sessão parece ter expirado; faça login manual e tente novamente.")
            await context.close()
            await browser.close()
            return 3

        # Overlays que podem interceptar o clique:
        # 1) modal promocional (ex.: Seguros Friday);
        # 2) banner de cookies do AdOpt.
        close_selector = (
            'button.close[data-dismiss="modal"][data-analytics-label*="Seguros Friday"]'
        )
        closed_modal = False
        for _ in range(20):  # espera até ~10s; o modal pode aparecer depois do load
            modal = page.locator("div.modal-aviso").filter(has_text="Seguros Friday").first
            if await modal.count() and await modal.is_visible():
                button = page.locator(close_selector).first
                if await button.count():
                    try:
                        await button.click(force=True)
                    except Exception:  # noqa: BLE001
                        await button.evaluate("el => el.click()")
                await page.wait_for_timeout(700)
                if await modal.is_visible():
                    await modal.evaluate("el => el.style.display = 'none'")
                # Remove backdrop residual do Bootstrap, se existir.
                await page.evaluate(
                    """() => {
                        document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
                        document.body.classList.remove('modal-open');
                    }"""
                )
                print("[modal] aviso Seguros Friday fechado")
                closed_modal = True
                break
            await page.wait_for_timeout(500)
        if not closed_modal:
            print("[modal] nenhum aviso Seguros Friday visível")

        try:
            reject = page.locator("#adopt-reject-all-button")
            await reject.wait_for(state="visible", timeout=6000)
            await reject.click()
            print("[cookies] banner fechado (Rejeitar cookies não necessários)")
            await page.wait_for_timeout(800)
        except Exception:  # noqa: BLE001
            print("[cookies] banner não apareceu ou já estava fechado")

        await page.wait_for_timeout(1500)
        card = page.locator("bspn-card", has_text="Parcelas em Atraso").first
        await card.wait_for(state="visible", timeout=30000)
        button = card.locator(".bspn-card-ver-detalhes-btn").first

        async def button_label() -> str:
            return " ".join((await button.inner_text()).split())

        async def is_open() -> bool:
            return "Ocultar" in await button_label()

        print(f"[card] 'Parcelas em Atraso' — botão atual: '{await button_label()}'")
        opened = await is_open()
        if opened:
            print("[info] card já estava aberto")
        else:
            for attempt in range(1, 3):
                print(f"[clique] tentativa {attempt}: Ver detalhes")
                try:
                    async with page.expect_response(
                        lambda response: "/api/parcelas/v1/list" in response.url,
                        timeout=30000,
                    ) as response_info:
                        await button.click()
                    response = await response_info.value
                    print(f"[rede] {response.status} {safe_url(response.url)}")
                    opened = True
                    break
                except Exception:  # noqa: BLE001
                    print("[aviso] resposta de /api/parcelas/v1/list não chegou a tempo")
                await page.wait_for_timeout(2000)
                if await is_open():
                    opened = True
                    break
                print("[aviso] o card não abriu; aguardando e tentando novamente")

        if not opened:
            print("[aviso] não foi possível confirmar a abertura do card; capturando mesmo assim")

        with suppress(Exception):
            await page.wait_for_load_state("networkidle", timeout=20000)
        await page.wait_for_timeout(4000)

        # Salva corpos das chamadas de interesse (podem conter PII; data/ é ignorado)
        payload_index: list[dict[str, object]] = []
        for idx, response in interesting:
            try:
                body = await response.text()
            except Exception as exc:  # noqa: BLE001
                payload_index.append({"url": safe_url(response.url), "error": str(exc)})
                continue
            suffix = "html" if "html" in response.headers.get("content-type", "") else "json"
            path = payloads / f"payload_{idx:03d}.{suffix}"
            path.write_text(body, encoding="utf-8", errors="ignore")
            payload_index.append(
                {
                    "url": safe_url(response.url),
                    "status": response.status,
                    "file": str(path),
                    "bytes": len(body),
                }
            )
        (out / "payloads.json").write_text(
            json.dumps(payload_index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        final_url = safe_url(page.url)
        title = await page.title()
        await page.screenshot(path=str(out / "page.png"), full_page=True)
        (out / "page.html").write_text(await page.content(), encoding="utf-8")
        await context.storage_state(path=str(out / "state.json"))
        await context.tracing.stop(path=str(out / "trace.zip"))

        summary = {
            "slug": args.slug,
            "start_url": safe_url(args.url),
            "final_url": final_url,
            "title": title,
            "captured_at": stamp,
            "network_entries": len(entries),
            "interesting_payloads": payload_index,
            "output_dir": str(out),
        }
        (out / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        await context.close()
        await browser.close()

    print("\nCAPTURA CONCLUÍDA")
    print(f"URL final: {final_url}")
    print(f"Título   : {title}")
    print(f"Rede     : {len(entries)} entradas")
    print(f"Pasta    : {out}")
    print("\nChamadas de interesse:")
    for item in payload_index:
        print(f"- {item.get('status')} {item.get('url')} -> {item.get('file', item.get('error'))}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura Parcelas em Atraso (Bradesco Auto)")
    parser.add_argument("--url", required=True, help="URL da área Auto autenticada")
    parser.add_argument("--state", required=True, help="storage_state.json autenticado")
    parser.add_argument("--slug", default="bradesco", help="Nome da pasta de saída")
    parser.add_argument("--output-root", default="data/discovery", help="Raiz das capturas")
    parser.add_argument("--headless", action="store_true", help="Executar sem janela")
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
