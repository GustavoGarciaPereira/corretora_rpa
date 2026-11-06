from __future__ import annotations

from corretor.application.dto import CollectionOutcome
from corretor.domain.enums import RunStatus
from corretor.interfaces.cli import _print_outcomes


def test_print_outcomes_sinaliza_falha(capsys) -> None:
    outcomes = [
        CollectionOutcome(
            insurer_slug="demo",
            insurer_name="Seguradora Demo",
            status=RunStatus.FAILED,
            error="portal indisponível",
        )
    ]

    assert _print_outcomes(outcomes) is False
    assert "erro: portal indisponível" in capsys.readouterr().out


def test_print_outcomes_sinaliza_sucesso(capsys) -> None:
    outcomes = [
        CollectionOutcome(
            insurer_slug="demo",
            insurer_name="Seguradora Demo",
            status=RunStatus.SUCCESS,
        )
    ]

    assert _print_outcomes(outcomes) is True
    assert "[OK]" in capsys.readouterr().out
