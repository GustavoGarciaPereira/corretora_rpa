from __future__ import annotations

from datetime import date

from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates

from corretor.application.dto import OPEN_FILTER, InsurerHealth, PendencyFilters
from corretor.domain.enums import InsurerState, PendencyKind, WorkflowStatus
from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore


def filters_from_query(insurer: str, status: str, q: str, kind: str = "") -> PendencyFilters:
    return PendencyFilters(
        insurer_slug=insurer.strip(),
        status=status.strip(),
        q=q.strip(),
        kind=kind.strip(),
    )


def parse_status(value: str) -> WorkflowStatus:
    try:
        return WorkflowStatus(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Status inválido") from exc


def parse_optional_date(value: str, field: str = "data") -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field} inválida") from exc


def _attention_detail(item: InsurerHealth) -> str:
    return {
        InsurerState.FAILED: (
            "A coleta falhou. Tente novamente; se persistir, verifique a conexão "
            "ou a sessão do portal."
        ),
        InsurerState.PARTIAL: (
            "A coleta foi concluída parcialmente. Confira os detalhes antes de usar os números."
        ),
        InsurerState.NEEDS_ATTENTION: ("A sessão do portal expirou ou exige intervenção humana."),
        InsurerState.STALE: (
            "Os dados estão desatualizados; a última coleta bem-sucedida está fora do prazo."
        ),
        InsurerState.NEVER_COLLECTED: "Esta seguradora ainda não teve uma coleta concluída.",
    }[item.state]


def _error_items(health: list[InsurerHealth]) -> list[dict]:
    items: list[dict] = []
    for item in health:
        state = item.state
        if not state.needs_attention:
            continue
        if state is InsurerState.NEEDS_ATTENTION:
            retry_label = "Tentar novamente"
        elif state is InsurerState.STALE:
            retry_label = "Atualizar agora"
        elif state is InsurerState.NEVER_COLLECTED:
            retry_label = "Coletar agora"
        else:
            retry_label = "Tentar novamente"
        items.append(
            {
                "slug": item.slug,
                "name": item.name,
                "state": state,
                "detail": _attention_detail(item),
                "error": item.last_error,
                "when": item.last_run_at,
                "last_success_at": item.last_success_at,
                "retry_label": retry_label,
                "needs_session": state is InsurerState.NEEDS_ATTENTION,
            }
        )
    return items


def _attention_breakdown(health: list[InsurerHealth]) -> dict[str, int]:
    failed_states = {
        InsurerState.FAILED,
        InsurerState.PARTIAL,
        InsurerState.NEEDS_ATTENTION,
    }
    return {
        "failed": sum(1 for item in health if item.state in failed_states),
        "stale": sum(1 for item in health if item.state is InsurerState.STALE),
        "never": sum(1 for item in health if item.state is InsurerState.NEVER_COLLECTED),
    }


def _is_filtered(filters: PendencyFilters) -> bool:
    return bool(
        filters.insurer_slug or filters.q or filters.kind or filters.status not in ("", OPEN_FILTER)
    )


def dashboard_context(
    request: Request,
    store: SqlAlchemyStore,
    container: Container,
    filters: PendencyFilters,
    message: str = "",
    message_kind: str = "success",
) -> dict:
    today = container.clock.today()
    health = store.list_insurer_health(container.stale_before())
    attention_insurers = [item for item in health if item.state.needs_attention]
    return {
        "request": request,
        "pendencies": store.list_pendencies(filters, today),
        "summary": store.summary(today, container.stale_before()),
        "insurers": store.list_insurers(),
        "health": health,
        "health_by_slug": {item.slug: item for item in health},
        "attention_insurers": len(attention_insurers),
        "attention_breakdown": _attention_breakdown(health),
        "runs": store.list_runs(6),
        "filters": filters,
        "is_filtered": _is_filtered(filters),
        "statuses": list(WorkflowStatus),
        "kinds": list(PendencyKind),
        "today": today,
        "message": message,
        "message_kind": message_kind,
        "error_items": _error_items(health),
    }


def render_dashboard(
    templates: Jinja2Templates,
    request: Request,
    store: SqlAlchemyStore,
    container: Container,
    filters: PendencyFilters,
    *,
    partial: bool,
    message: str = "",
    message_kind: str = "success",
    attention: list | None = None,
):
    context = dashboard_context(
        request,
        store,
        container,
        filters,
        message=message,
        message_kind=message_kind,
    )
    context["attention"] = attention or []
    name = "partials/dashboard_content.html" if partial else "dashboard.html"
    return templates.TemplateResponse(request=request, name=name, context=context)
