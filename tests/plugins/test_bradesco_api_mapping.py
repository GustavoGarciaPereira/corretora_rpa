from __future__ import annotations

from datetime import date

import pytest

from corretor.domain.enums import PendencyKind
from corretor.domain.errors import AdapterError, ValidationError
from corretor.plugins.bradesco.api_mapping import map_api_payload


def payload() -> dict:
    return {
        "propostas": [
            {
                "proponente": {"nome": "Cliente Fictício", "cpfCnpjProponente": 123},
                "vigencia": {
                    "dtEfetivacao": "16/10/2026",
                    "dtInicioVigencia": "22/10/2026",
                    "dtFimVigencia": "22/10/2027",
                },
                "sucursal": "637",
                "agencia": "0000",
                "numProposta": "637077119",
                "tpProposta": "Renovação",
                "origem": "Portal",
                "modalidade": "R",
                "vencimento": {
                    "status": "Processando nova chance",
                    "dtVencimento": "29/10/2026",
                    "formaPagamento": "Boleto",
                },
                "criticas": [{"descricao": "Crítica fictícia"}],
                "statusVistoria": "6",
                "statusRastreador": "5",
                "statusRetificacao": "1",
                "statusLivelo": {"pendente": True},
            }
        ]
    }


def test_mapeia_proposta_da_api_oficial() -> None:
    items = map_api_payload(payload())
    assert len(items) == 1
    item = items[0]
    assert item.kind is PendencyKind.PROPOSTA
    assert item.policy_number == "637-0000/637077119"
    assert item.insured_name == "Cliente Fictício"
    assert item.branch == "Renovação / R / Portal"
    assert item.installment_number == 1
    assert item.due_date == date(2026, 10, 29)
    assert item.amount_cents == 0
    assert item.payment_method == "Boleto"
    assert item.adjusted_vigency == "22/10/2026 a 22/10/2027"
    assert item.insurer_status == "Processando nova chance"
    assert item.external_id == "637077119"
    assert "Crítica fictícia" in item.alerts
    assert "Vistoria: 6" in item.alerts
    assert "Rastreador: 5" in item.alerts
    assert "Retificação: 1" in item.alerts
    assert "Livelo pendente" in item.alerts


def test_lista_vazia_e_valida() -> None:
    assert map_api_payload({"propostas": []}) == []


def test_mensagem_erro_falha_explicitamente() -> None:
    with pytest.raises(AdapterError, match="manutenção"):
        map_api_payload({"mensagemErro": {"dsErro": "manutenção"}})


def test_vencimento_invalido_falha() -> None:
    data = payload()
    data["propostas"][0]["vencimento"]["dtVencimento"] = ""
    with pytest.raises(ValidationError):
        map_api_payload(data)
