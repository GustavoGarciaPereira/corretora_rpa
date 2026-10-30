from __future__ import annotations

from datetime import date

from corretor.application.logic import compute_diff
from corretor.application.ports import ExistingInstallment, Snapshot
from corretor.domain.entities import Installment, Pendency, RawInstallment
from corretor.domain.enums import PendencyKind, WorkflowStatus


def raw(number: int = 1, due: date = date(2026, 11, 10)) -> RawInstallment:
    return RawInstallment(
        policy_number="0001",
        insured_name="Cliente Fictício",
        branch="Auto",
        installment_number=number,
        due_date=due,
        amount_cents=10_000,
    )


def existing(
    *,
    active: bool,
    status: WorkflowStatus,
    number: int = 1,
    due: date = date(2026, 11, 10),
) -> ExistingInstallment:
    installment = Installment(
        id=1,
        policy_id=1,
        number=number,
        due_date=due,
        amount_cents=10_000,
        is_active=active,
    )
    pendency = Pendency(
        id=1,
        installment_id=1,
        workflow_status=status,
    )
    return ExistingInstallment(
        kind=PendencyKind.PARCELA,
        policy_number="0001",
        installment=installment,
        pendency=pendency,
    )


def snapshot_with(item: ExistingInstallment) -> Snapshot:
    key = (PendencyKind.PARCELA, "0001", 1, item.installment.due_date)
    return Snapshot(policies={}, items={key: item})


def test_primeira_coleta_marca_tudo_como_novo() -> None:
    diff = compute_diff(Snapshot(policies={}, items={}), [raw()])
    assert len(diff.new) == 1
    assert diff.missing == ()


def test_parcela_ausente_em_snapshot_ativo_e_resolvida() -> None:
    item = existing(active=True, status=WorkflowStatus.DETECTADA)
    snapshot = snapshot_with(item)
    diff = compute_diff(snapshot, [])
    assert len(diff.missing) == 1
    assert diff.resolved_count == 1


def test_parcela_regularizada_reaparece_como_reaberta() -> None:
    item = existing(active=False, status=WorkflowStatus.REGULARIZADA)
    snapshot = snapshot_with(item)
    diff = compute_diff(snapshot, [raw()])
    assert len(diff.reopened) == 1
    assert diff.new == ()


def test_parcela_descartada_reaparece_sem_reabrir() -> None:
    item = existing(active=False, status=WorkflowStatus.DESCARTADA)
    snapshot = snapshot_with(item)
    diff = compute_diff(snapshot, [raw()])
    assert len(diff.discarded_reappeared) == 1
    assert diff.reopened == ()


def test_parcela_ativa_vista_nao_gera_novo_nem_ausente() -> None:
    item = existing(active=True, status=WorkflowStatus.EM_ANALISE)
    snapshot = snapshot_with(item)
    diff = compute_diff(snapshot, [raw()])
    assert diff.new == ()
    assert diff.missing == ()
