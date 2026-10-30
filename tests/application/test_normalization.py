from __future__ import annotations

from datetime import date, datetime

import pytest

from corretor.application.logic import normalize_items
from corretor.domain.entities import RawInstallment
from corretor.domain.errors import ValidationError


def raw(**overrides) -> RawInstallment:
    data = {
        "policy_number": " 0001 ",
        "insured_name": " Cliente Fictício ",
        "branch": " Auto ",
        "installment_number": 3,
        "due_date": date(2026, 11, 10),
        "amount_cents": 12_345,
        "producer": " Beto ",
    }
    data.update(overrides)
    return RawInstallment(**data)


def test_normaliza_campos_e_preserva_dados() -> None:
    items = normalize_items([raw()])
    assert len(items) == 1
    item = items[0]
    assert item.policy_number == "0001"
    assert item.insured_name == "Cliente Fictício"
    assert item.branch == "Auto"
    assert item.producer == "Beto"


def test_rejeita_duplicata_no_snapshot() -> None:
    with pytest.raises(ValidationError):
        normalize_items([raw(), raw()])


def test_rejeita_vencimento_datetime() -> None:
    with pytest.raises(ValidationError):
        normalize_items([raw(due_date=datetime(2026, 11, 10, 12, 0))])


def test_rejeita_valor_negativo() -> None:
    with pytest.raises(ValidationError):
        normalize_items([raw(amount_cents=-1)])


def test_rejeita_segurado_sem_nome() -> None:
    with pytest.raises(ValidationError):
        normalize_items([raw(insured_name="  ")])
