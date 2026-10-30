from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from fastapi.templating import Jinja2Templates

from corretor.infrastructure.container import Container
from corretor.infrastructure.persistence import SqlAlchemyStore


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_templates(request: Request) -> Jinja2Templates:
    return request.app.state.templates


def get_store(request: Request) -> Iterator[SqlAlchemyStore]:
    container: Container = request.app.state.container
    with container.session() as store:
        yield store
