from __future__ import annotations

from collections.abc import Iterator

import pytest

from corretor.infrastructure.config import Settings
from corretor.infrastructure.container import Container


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        evidence_dir=tmp_path / "evidence",
        enable_scheduler=False,
        seed_demo=False,
        plugin_paths="",
        bradesco_state_path=tmp_path / "bradesco-state.json",
        log_level="WARNING",
    )


@pytest.fixture
def container(settings: Settings) -> Container:
    instance = Container(settings)
    instance.init_db()
    return instance


@pytest.fixture
def store(container: Container) -> Iterator:
    with container.session() as session:
        yield session
