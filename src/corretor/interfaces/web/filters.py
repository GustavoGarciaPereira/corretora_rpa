from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def brl(cents: int | None) -> str:
    value = (cents or 0) / 100
    formatted = f"{value:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def datebr(value: date | datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d/%m/%Y")


def datetimebr(value: datetime | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(SAO_PAULO).strftime("%d/%m/%Y %H:%M")


def short(value: str | None, length: int = 90) -> str:
    text = (value or "").strip()
    if len(text) <= length:
        return text
    return text[: length - 1] + "…"


def register_filters(env: Environment) -> None:
    env.filters["brl"] = brl
    env.filters["datebr"] = datebr
    env.filters["datetimebr"] = datetimebr
    env.filters["short"] = short
