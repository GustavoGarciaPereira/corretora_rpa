from __future__ import annotations

from collections.abc import Sequence

from corretor.domain.entities import RawInstallment, installment_key
from corretor.domain.enums import REOPENABLE_STATUSES, WorkflowStatus

from ..ports import DiffResult, Snapshot


def compute_diff(snapshot: Snapshot, incoming: Sequence[RawInstallment]) -> DiffResult:
    """Calcula o que é novo, reaberto, ausente e descartado.

    Função pura: não grava nada. O Store aplica o resultado em transação.
    """
    incoming_by_key = {
        installment_key(item.kind, item.policy_number, item.installment_number, item.due_date): item
        for item in incoming
    }

    new: list[RawInstallment] = []
    reopened: list[RawInstallment] = []
    discarded: list[RawInstallment] = []

    for key, item in incoming_by_key.items():
        existing = snapshot.items.get(key)
        if existing is None:
            new.append(item)
            continue
        status = existing.pendency.workflow_status
        if not existing.installment.is_active and status in REOPENABLE_STATUSES:
            reopened.append(item)
        elif not existing.installment.is_active and status is WorkflowStatus.DESCARTADA:
            discarded.append(item)

    missing = [
        existing
        for key, existing in snapshot.items.items()
        if existing.installment.is_active and key not in incoming_by_key
    ]

    return DiffResult(
        incoming=tuple(incoming_by_key.values()),
        new=tuple(new),
        reopened=tuple(reopened),
        missing=tuple(missing),
        discarded_reappeared=tuple(discarded),
    )
