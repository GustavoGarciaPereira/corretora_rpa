from __future__ import annotations

from datetime import date

from corretor.application.dto import PendencyFilters
from corretor.application.ports import AdapterProvider
from corretor.application.services import CollectionService
from corretor.domain.entities import AdapterManifest, RawInstallment
from corretor.domain.enums import RunStatus, WorkflowStatus
from corretor.domain.errors import AdapterError
from corretor.domain.ports import InsurerAdapter


def raw(number: int, policy: str = "0001", due: date = date(2026, 11, 10)) -> RawInstallment:
    return RawInstallment(
        policy_number=policy,
        insured_name="Cliente Fictício",
        branch="Auto",
        installment_number=number,
        due_date=due,
        amount_cents=10_000,
        producer="Beto",
    )


class StaticAdapter:
    def __init__(self, items: list[RawInstallment], fail: bool = False) -> None:
        self.manifest = AdapterManifest(slug="demo", name="Demo", version="0.1.0")
        self.items = items
        self.fail = fail

    def fetch_pending(self) -> list[RawInstallment]:
        if self.fail:
            raise AdapterError("portal indisponível")
        return list(self.items)


class StubProvider(AdapterProvider):
    def __init__(self, adapter: InsurerAdapter) -> None:
        self.adapter = adapter

    def get(self, slug: str) -> InsurerAdapter:
        return self.adapter

    def has(self, slug: str) -> bool:
        return slug == "demo"

    def manifests(self):
        return [self.adapter.manifest]


def service_for(container, store, adapter: StaticAdapter) -> CollectionService:
    return CollectionService(
        store=store,
        provider=StubProvider(adapter),
        evidence=container.evidence,
        clock=container.clock,
    )


def test_coleta_e_idempotente_e_regulariza_ausente(container, store) -> None:
    store.create_insurer("demo", "Seguradora Demo", "demo")
    adapter = StaticAdapter([raw(1), raw(2)])
    service = service_for(container, store, adapter)
    today = container.clock.today()

    first = service.collect("demo")
    assert first.status is RunStatus.SUCCESS
    assert first.new_count == 2
    assert len(store.list_pendencies(PendencyFilters(), today)) == 2

    second = service.collect("demo")
    assert second.new_count == 0
    assert len(store.list_pendencies(PendencyFilters(), today)) == 2

    adapter.items = [raw(1)]
    third = service.collect("demo")
    assert third.resolved_count == 1
    views = store.list_pendencies(PendencyFilters(), today)
    statuses = {view.installment_number: view.workflow_status for view in views}
    assert statuses[1] is WorkflowStatus.DETECTADA
    assert statuses[2] is WorkflowStatus.REGULARIZADA


def test_falha_nao_apaga_dados_e_registra_run(container, store) -> None:
    store.create_insurer("demo", "Seguradora Demo", "demo")
    adapter = StaticAdapter([raw(1)])
    service = service_for(container, store, adapter)
    today = container.clock.today()

    assert service.collect("demo").status is RunStatus.SUCCESS
    adapter.fail = True
    outcome = service.collect("demo")

    assert outcome.status is RunStatus.FAILED
    assert "portal indisponível" in outcome.error
    runs = store.list_runs(1)
    assert runs[0].status is RunStatus.FAILED
    assert runs[0].evidence_path
    views = store.list_pendencies(PendencyFilters(), today)
    assert len(views) == 1
    assert views[0].workflow_status is WorkflowStatus.DETECTADA


def test_collect_all_com_plugin_demo_real(container, store) -> None:
    store.create_insurer("demo", "Seguradora Demo", "demo")
    outcomes = container.collection_service(store).collect_all()
    assert len(outcomes) == 1
    assert outcomes[0].ok
    assert outcomes[0].items_found == 5
