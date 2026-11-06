from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from corretor.application.dto import InsurerHealth
from corretor.domain.enums import InsurerState, RunStatus

NOW = datetime(2026, 11, 6, 12, 0)


def make_health(**overrides) -> InsurerHealth:
    values = {
        "slug": "demo",
        "name": "Seguradora Demo",
        "active": True,
        "last_run_at": NOW - timedelta(hours=1),
        "last_success_at": NOW - timedelta(hours=1),
        "is_stale": False,
        "last_status": RunStatus.SUCCESS,
        "last_error": "",
    }
    values.update(overrides)
    return InsurerHealth(**values)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"active": False}, InsurerState.DISABLED),
        (
            {
                "last_run_at": None,
                "last_success_at": None,
                "last_status": None,
                "is_stale": True,
            },
            InsurerState.NEVER_COLLECTED,
        ),
        (
            {"last_success_at": None, "last_status": RunStatus.FAILED, "is_stale": True},
            InsurerState.FAILED,
        ),
        ({"last_status": RunStatus.PARTIAL}, InsurerState.PARTIAL),
        ({"last_status": RunStatus.NEEDS_ATTENTION}, InsurerState.NEEDS_ATTENTION),
        ({"last_status": RunStatus.RUNNING}, InsurerState.RUNNING),
        (
            {
                "last_run_at": NOW - timedelta(hours=48),
                "last_success_at": NOW - timedelta(hours=48),
                "is_stale": True,
            },
            InsurerState.STALE,
        ),
        ({}, InsurerState.OK),
    ],
)
def test_insurer_state(overrides, expected) -> None:
    assert make_health(**overrides).state is expected


def test_attention_states() -> None:
    assert InsurerState.OK.needs_attention is False
    assert InsurerState.RUNNING.needs_attention is False
    assert InsurerState.DISABLED.needs_attention is False
    assert InsurerState.FAILED.needs_attention is True
    assert InsurerState.PARTIAL.needs_attention is True
    assert InsurerState.NEEDS_ATTENTION.needs_attention is True
    assert InsurerState.STALE.needs_attention is True
    assert InsurerState.NEVER_COLLECTED.needs_attention is True
