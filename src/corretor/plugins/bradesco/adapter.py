from __future__ import annotations

import logging
from pathlib import Path

from corretor.domain.entities import AdapterManifest, PluginContext, RawInstallment
from corretor.domain.errors import (
    AdapterError,
    AdapterNotConfigured,
    AdapterSessionExpired,
)

from .mapping import map_payload
from .proposals import parse_proposals_html

logger = logging.getLogger(__name__)

REFERER = (
    "https://wwwn.bradescoseguros.com.br/pnegocios/wps/myportal/portalnegocios/arealogada/auto/"
)


class BradescoAdapter:
    manifest: AdapterManifest

    def __init__(self, manifest: AdapterManifest, context: PluginContext) -> None:
        self.manifest = manifest
        self.state_path = Path(str(context.get("bradesco_state_path", ""))).expanduser()
        self.endpoint = str(context.get("bradesco_endpoint", ""))
        self.proposals_endpoint = str(context.get("bradesco_proposals_endpoint", ""))
        self.collect_proposals = bool(context.get("bradesco_collect_proposals", True))
        self.headless = bool(context.get("bradesco_headless", True))
        self.timeout_ms = int(context.get("bradesco_timeout_ms", 60_000))

    def _get(self, context, url: str, accept: str):
        response = context.request.get(
            url,
            headers={"Accept": accept, "Referer": REFERER},
            timeout=self.timeout_ms,
        )
        if response.status in (401, 403) or "login" in response.url.lower():
            raise AdapterSessionExpired("sessão do Bradesco expirada; refaça o login manual")
        if not response.ok:
            raise AdapterError(f"Bradesco respondeu HTTP {response.status} em {url}")
        return response

    def fetch_pending(self) -> list[RawInstallment]:
        if not self.endpoint:
            raise AdapterNotConfigured("BRADESCO_ENDPOINT não configurado")
        if self.collect_proposals and not self.proposals_endpoint:
            raise AdapterNotConfigured("BRADESCO_PROPOSALS_ENDPOINT não configurado")
        if not self.state_path.exists():
            raise AdapterNotConfigured(
                "sessão do Bradesco não encontrada em "
                f"{self.state_path}. Gere o state.json com login manual "
                "(tools/discover_portal.py) e configure BRADESCO_STATE_PATH."
            )

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise AdapterNotConfigured(
                "Playwright não instalado. Instale o extra 'rpa': uv pip install -e '.[rpa]'"
            ) from exc

        items: list[RawInstallment] = []
        try:
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=self.headless, channel="chrome")
                except Exception:  # noqa: BLE001 - fallback para Chromium do Playwright
                    browser = playwright.chromium.launch(headless=self.headless)

                context = browser.new_context(
                    locale="pt-BR",
                    timezone_id="America/Sao_Paulo",
                    storage_state=str(self.state_path),
                )
                try:
                    response = self._get(context, self.endpoint, "application/json")
                    items.extend(map_payload(response.json()))

                    if self.collect_proposals:
                        proposals = self._get(context, self.proposals_endpoint, "text/html")
                        items.extend(parse_proposals_html(proposals.text()))
                finally:
                    context.close()
                    browser.close()
        except (AdapterError, AdapterNotConfigured, AdapterSessionExpired):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("falha ao consultar o Bradesco")
            raise AdapterError(f"falha ao consultar o Bradesco: {exc.__class__.__name__}") from exc

        return items


__all__ = ["BradescoAdapter"]
