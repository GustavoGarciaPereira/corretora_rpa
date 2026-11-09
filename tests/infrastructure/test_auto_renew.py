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


def test_coleta_nao_bloqueia_e_inicia_renovacao(container, monkeypatch) -> None:
    fake = FakeCollectionService()
    monkeypatch.setattr(container, "collection_service", lambda store: fake)
    monkeypatch.setattr(container.renewal, "auto_available", lambda: True)
    started: list[tuple[bool, bool]] = []

    def fake_start(*, auto: bool = False, respect_cooldown: bool = False):
        started.append((auto, respect_cooldown))
        return RenewalStatus("running", "entrando no portal")

    monkeypatch.setattr(container.renewal, "start", fake_start)
    monkeypatch.setattr(
        container.renewal,
        "auto_renew",
        lambda: (_ for _ in ()).throw(AssertionError("não deve bloquear")),
    )

    outcomes = container.collect_all(wait_for_renewal=False)

    assert fake.calls == 1
    assert started == [(True, True)]
    assert outcomes[0].status is RunStatus.NEEDS_ATTENTION
    assert outcomes[0].renewal_started is True


class FakeSingleCollectionService:
    def __init__(self) -> None:
        self.calls = 0

    def ensure_insurer(self, slug: str) -> None:
        pass

    def collect(self, slug: str) -> CollectionOutcome:
        self.calls += 1
        return CollectionOutcome(
            insurer_slug=slug,
            insurer_name="Bradesco Seguros",
            status=RunStatus.NEEDS_ATTENTION,
            error="sessão expirada",
        )


def test_coleta_individual_nao_bloqueia(container, monkeypatch) -> None:
    fake = FakeSingleCollectionService()
    monkeypatch.setattr(container, "collection_service", lambda store: fake)
    monkeypatch.setattr(container.renewal, "auto_available", lambda: True)
    monkeypatch.setattr(
        container.renewal,
        "start",
        lambda **kwargs: RenewalStatus("running", "entrando no portal"),
    )

    outcome = container.collect("bradesco", wait_for_renewal=False)

    assert fake.calls == 1
    assert outcome.renewal_started is True


def test_coleta_com_auto_renew_desligado_nao_inicia(container, monkeypatch) -> None:
    fake = FakeCollectionService()
    monkeypatch.setattr(container, "collection_service", lambda store: fake)
    monkeypatch.setattr(container.renewal, "auto_available", lambda: True)
    monkeypatch.setattr(
        container.renewal,
        "start",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("não deve renovar")),
    )

    outcomes = container.collect_all(auto_renew=False)

    assert fake.calls == 1
    assert outcomes[0].renewal_started is False
