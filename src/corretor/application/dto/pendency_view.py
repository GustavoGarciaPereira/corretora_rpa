from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from corretor.domain.enums import PendencyKind, WorkflowStatus


@dataclass(frozen=True, slots=True)
class PendencyView:
    id: int
    insurer_id: int
    insurer_name: str
    insurer_slug: str
    kind: PendencyKind
    policy_id: int
    insured_name: str
    policy_number: str
    branch: str
    installment_number: int
    due_date: date
    amount_cents: int
    boleto_url: str
    boleto_code: str
    external_id: str
    alerts: str
    payment_method: str
    adjusted_vigency: str
    insurer_status: str
    workflow_status: WorkflowStatus
    action: str
    action_date: date | None
    new_due_date: date | None
    deadline: date | None
    assigned_to: str
    producer: str
    today: date

    @property
    def days_until_due(self) -> int:
        return (self.due_date - self.today).days

    @property
    def is_overdue(self) -> bool:
        return self.workflow_status.is_open and self.days_until_due < 0

    @property
    def is_due_soon(self) -> bool:
        return self.workflow_status.is_open and 0 <= self.days_until_due <= 7

    @property
    def days_overdue(self) -> int:
        return max(0, -self.days_until_due)

    @property
    def spreadsheet_status(self) -> str:
        if self.workflow_status is WorkflowStatus.VENCIDA:
            return "VENCIDA"
        if self.workflow_status is WorkflowStatus.REGULARIZADA:
            return "REGULARIZADA"
        if self.workflow_status is WorkflowStatus.DESCARTADA:
            return "DESCARTADA"
        return "PENDENTE"
