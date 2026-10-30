from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def is_logged_in_url(url: str) -> bool:
    """Confirma a área logada pelo path, não pelo parâmetro target da URL.

    A página de login recebe ``target=.../arealogada/`` na query string. Procurar
    "arealogada" na URL inteira causava falso positivo e salvava uma sessão sem
    autenticação.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "login.bradescoseguros.com.br":
        return False
    return (
        host == "bradescoseguros.com.br" or host.endswith(".bradescoseguros.com.br")
    ) and "/arealogada" in parsed.path.lower()


async def is_logged_in_page(page: Any, stabilization_ms: int = 2000) -> bool:
    """Confirma a área logada com URL estável e menu autenticado visível."""
    if not is_logged_in_url(page.url):
        return False
    await page.wait_for_timeout(stabilization_ms)
    if not is_logged_in_url(page.url):
        return False
    for text in ("Minha carteira", "Meus Leads"):
        marker = page.get_by_text(text, exact=False)
        if await marker.count() and await marker.first.is_visible():
            return True
    return False
