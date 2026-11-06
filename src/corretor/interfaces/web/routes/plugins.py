from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore

from ..dependencies import get_container, get_store, get_templates

router = APIRouter()


@router.get("/plugins", response_class=HTMLResponse)
def plugins(
    request: Request,
    store: SqlAlchemyStore = Depends(get_store),
    container: Container = Depends(get_container),
    templates: Jinja2Templates = Depends(get_templates),
):
    health = store.list_insurer_health(container.stale_before())
    manifests = container.plugins.manifests()
    manifest_slugs = {manifest.slug for manifest in manifests}
    orphan_insurers = [item for item in health if item.slug not in manifest_slugs]
    return templates.TemplateResponse(
        request=request,
        name="plugins.html",
        context={
            "request": request,
            "manifests": manifests,
            "plugin_errors": container.plugins.errors,
            "health_by_slug": {item.slug: item for item in health},
            "orphan_insurers": orphan_insurers,
            "bradesco_state_exists": container.settings.bradesco_state_path.exists(),
            "bradesco_state_path": container.settings.bradesco_state_path,
        },
    )
