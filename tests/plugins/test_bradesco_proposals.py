from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from corretor.domain.enums import PendencyKind
from corretor.domain.errors import AdapterError
from corretor.plugins.bradesco.proposals import parse_proposals_html

FIXTURE = Path(__file__).parent / "fixtures" / "propostas_pendentes.html"


def test_mapeia_proposta_pendente() -> None:
    items = parse_proposals_html(FIXTURE.read_text(encoding="utf-8"))
    assert len(items) == 1
    item = items[0]
    assert item.kind is PendencyKind.PROPOSTA
    assert item.policy_number == "123-0000/123456789"
    assert item.insured_name == "Cliente Fictício"
    assert item.branch == "Individual"
    assert item.installment_number == 1
    assert item.due_date == date(2026, 10, 29)
    assert item.amount_cents == 155_818
    assert item.boleto_code == "20000000001"
    assert item.external_id == "123456789"
    assert item.producer == "12345"
    assert item.payment_method == "Boleto"
    assert item.adjusted_vigency == "22/10/2026 a 22/10/2027"
    assert item.insurer_status == "Processando nova chance"
    assert "Processando nova chance" in item.alerts


def test_tabela_vazia_e_valida() -> None:
    html = (
        '<table id="propostas-pendentes" data-qtd-propostas-pendentes="0"><tbody></tbody></table>'
    )
    assert parse_proposals_html(html) == []


def test_quantidade_divergente_falha() -> None:
    html = (
        '<table id="propostas-pendentes" data-qtd-propostas-pendentes="2"><tbody></tbody></table>'
    )
    with pytest.raises(AdapterError, match="divergente"):
        parse_proposals_html(html)


def test_sem_tabela_falha() -> None:
    with pytest.raises(AdapterError, match="não encontrada"):
        parse_proposals_html("<html><body>erro inesperado</body></html>")
