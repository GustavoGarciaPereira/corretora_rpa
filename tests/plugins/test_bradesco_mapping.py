from __future__ import annotations

from datetime import date

import pytest

from corretor.domain.errors import AdapterError, ValidationError
from corretor.plugins.bradesco.mapping import map_payload


def payload() -> dict:
    return {
        "situacaoSistemas": {"sistemasDisponiveis": True, "mensagem": ""},
        "parcelas": [
            {
                "idParcela": 987,
                "segurado": {
                    "nome": "Cliente Fictício",
                    "cpfCnpj": "00000000000",
                    "email": "ficticio@example.com",
                    "telefones": [],
                },
                "corretor": {"codigo": "12345"},
                "sucursal": "637",
                "agenciaProdutora": "0000",
                "apolice": 637077119,
                "item": 1,
                "endosso": "00",
                "prestacao": "5",
                "pagamento": "Boleto",
                "premio": 123.45,
                "vencimento": "10/11/2026",
                "dataLimite": "15/11/2026",
                "vigAjustada": "01/11/2026 a 01/11/2027",
                "criticidade": True,
                "ramoSeguro": 990,
                "companhiaSeguradora": 1,
                "parcSistemaCobranca": "123",
                "dvParcSistemaCobranca": 4,
                "modalidade": "Auto",
                "qtdOutrasParcelas": 2,
                "sinistro": False,
                "apoliceEmCancelamento": False,
            }
        ],
    }


def test_mapeia_payload_para_raw_installment() -> None:
    items = map_payload(payload())
    assert len(items) == 1
    item = items[0]
    assert item.policy_number == "637-0000/637077119/1"
    assert item.insured_name == "Cliente Fictício"
    assert item.branch == "Auto"
    assert item.installment_number == 5
    assert item.due_date == date(2026, 11, 10)
    assert item.amount_cents == 12_345
    assert item.deadline == date(2026, 11, 15)
    assert item.boleto_code == "1234"
    assert item.external_id == "987"
    assert item.producer == "12345"
    assert item.payment_method == "Boleto"
    assert item.adjusted_vigency == "01/11/2026 a 01/11/2027"
    assert "Com crítica" in item.alerts
    assert "2 outra(s) parcela(s)" in item.alerts


def test_payload_vazio_e_valido() -> None:
    data = payload()
    data["parcelas"] = []
    assert map_payload(data) == []


def test_sistemas_indisponiveis_falha_explicitamente() -> None:
    data = payload()
    data["situacaoSistemas"] = {
        "sistemasDisponiveis": False,
        "mensagem": "manutenção",
    }
    with pytest.raises(AdapterError, match="manutenção"):
        map_payload(data)


def test_vencimento_invalido_falha() -> None:
    data = payload()
    data["parcelas"][0]["vencimento"] = ""
    with pytest.raises(ValidationError):
        map_payload(data)
