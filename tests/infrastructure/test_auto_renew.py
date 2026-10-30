from __future__ import annotations

from corretor.application.dto import CollectionOutcome
from corretor.domain.enums import RunStatus
from corretor.infrastructure.renewal import RenewalStatus


class FakeCollectionService:
    def __init__(self) -> None:
        self.calls = 0

    def collect_all(self):
        self.calls += 1
        if self.calls == 1:
            return [
                CollectionOutcome(
                    insurer_slug="bradesco",
                    insurer_name="Bradesco Seguros",
                    status=RunStatus.NEEDS_ATTENTION,
                    error="sessão expirada",
                )
            ]
        return [
            CollectionOutcome(
                insurer_slug="bradesco",
                insurer_name="Bradesco Seguros",
                status=RunStatus.SUCCESS,
                items_found=1,
                new_count=1,
            )
        ]


def test_coleta_renova_e_repete_quando_sessao_expira(container, monkeypatch) -> None:
    fake = FakeCollectionService()
    monkeypatch.setattr(container, "collection_service", lambda store: fake)
    monkeypatch.setattr(container.renewal, "auto_available", lambda: True)
    monkeypatch.setattr(
        container.renewal,
        "auto_renew",
        lambda: RenewalStatus("success", "sessão renovada"),
    )

    outcomes = container.collect_all()

    assert fake.calls == 2
    assert outcomes[0].ok


def test_coleta_nao_renova_sem_credenciais(container, monkeypatch) -> None:
    fake = FakeCollectionService()
    monkeypatch.setattr(container, "collection_service", lambda store: fake)
    monkeypatch.setattr(container.renewal, "auto_available", lambda: False)

    outcomes = container.collect_all()

    assert fake.calls == 1
    assert outcomes[0].status is RunStatus.NEEDS_ATTENTION
