from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from corretor.application.dto import (
    OPEN_FILTER,
    OVERDUE_FILTER,
    InsurerHealth,
    PendencyDetail,
    PendencyFilters,
    PendencyUpdate,
    PendencyView,
    RunView,
    Summary,
)
from corretor.application.ports import (
    ApplyStats,
    DiffResult,
    ExistingInstallment,
    Snapshot,
)
from corretor.domain.entities import (
    CollectionRun,
    Installment,
    Insurer,
    Pendency,
    PendencyEvent,
    Policy,
    installment_key,
)
from corretor.domain.enums import OPEN_STATUSES, PendencyKind, RunStatus, WorkflowStatus

from .models import (
    CollectionRunModel,
    InstallmentModel,
    InsurerModel,
    PendencyEventModel,
    PendencyModel,
    PolicyModel,
)

OPEN_VALUES = tuple(status.value for status in OPEN_STATUSES)


def _insurer(model: InsurerModel) -> Insurer:
    return Insurer(
        id=model.id,
        slug=model.slug,
        name=model.name,
        adapter=model.adapter,
        active=model.active,
        last_run_at=model.last_run_at,
        last_success_at=model.last_success_at,
    )


def _policy(model: PolicyModel) -> Policy:
    return Policy(
        id=model.id,
        insurer_id=model.insurer_id,
        policy_number=model.policy_number,
        insured_name=model.insured_name,
        branch=model.branch,
        producer=model.producer,
        kind=PendencyKind(model.kind),
    )


def _installment(model: InstallmentModel) -> Installment:
    return Installment(
        id=model.id,
        policy_id=model.policy_id,
        number=model.number,
        due_date=model.due_date,
        amount_cents=model.amount_cents,
        boleto_url=model.boleto_url,
        boleto_code=model.boleto_code,
        external_id=model.external_id,
        alerts=model.alerts,
        payment_method=model.payment_method,
        adjusted_vigency=model.adjusted_vigency,
        insurer_status=model.insurer_status,
        is_active=model.is_active,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
    )


def _pendency(model: PendencyModel) -> Pendency:
    return Pendency(
        id=model.id,
        installment_id=model.installment_id,
        workflow_status=WorkflowStatus(model.workflow_status),
        action=model.action,
        action_date=model.action_date,
        new_due_date=model.new_due_date,
        deadline=model.deadline,
        assigned_to=model.assigned_to,
        notes=model.notes,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _event(model: PendencyEventModel) -> PendencyEvent:
    return PendencyEvent(
        id=model.id,
        pendency_id=model.pendency_id,
        from_status=WorkflowStatus(model.from_status) if model.from_status else None,
        to_status=WorkflowStatus(model.to_status),
        note=model.note,
        created_at=model.created_at,
    )


def _run(model: CollectionRunModel) -> CollectionRun:
    return CollectionRun(
        id=model.id,
        insurer_id=model.insurer_id,
        status=RunStatus(model.status),
        started_at=model.started_at,
        finished_at=model.finished_at,
        items_found=model.items_found,
        new_count=model.new_count,
        resolved_count=model.resolved_count,
        error=model.error,
        evidence_path=model.evidence_path,
    )


def _view(
    pendency: PendencyModel,
    installment: InstallmentModel,
    policy: PolicyModel,
    insurer: InsurerModel,
    today: date,
) -> PendencyView:
    return PendencyView(
        id=pendency.id,
        insurer_id=insurer.id,
        insurer_name=insurer.name,
        insurer_slug=insurer.slug,
        kind=PendencyKind(policy.kind),
        policy_id=policy.id,
        insured_name=policy.insured_name,
        policy_number=policy.policy_number,
        branch=policy.branch,
        installment_number=installment.number,
        due_date=installment.due_date,
        amount_cents=installment.amount_cents,
        boleto_url=installment.boleto_url,
        boleto_code=installment.boleto_code,
        external_id=installment.external_id,
        alerts=installment.alerts,
        payment_method=installment.payment_method,
        adjusted_vigency=installment.adjusted_vigency,
        insurer_status=installment.insurer_status,
        workflow_status=WorkflowStatus(pendency.workflow_status),
        action=pendency.action,
        action_date=pendency.action_date,
        new_due_date=pendency.new_due_date,
        deadline=pendency.deadline,
        assigned_to=pendency.assigned_to,
        producer=policy.producer,
        today=today,
    )


class SqlAlchemyStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_insurer_by_slug(self, slug: str) -> Insurer | None:
        model = self.session.scalar(select(InsurerModel).where(InsurerModel.slug == slug))
        return _insurer(model) if model else None

    def list_insurers(self) -> list[Insurer]:
        models = self.session.scalars(select(InsurerModel).order_by(InsurerModel.name)).all()
        return [_insurer(model) for model in models]

    def list_active_insurers(self) -> list[Insurer]:
        models = self.session.scalars(
            select(InsurerModel).where(InsurerModel.active.is_(True)).order_by(InsurerModel.name)
        ).all()
        return [_insurer(model) for model in models]

    def create_insurer(self, slug: str, name: str, adapter: str, active: bool = True) -> Insurer:
        existing = self.session.scalar(select(InsurerModel).where(InsurerModel.slug == slug))
        if existing is not None:
            return _insurer(existing)
        model = InsurerModel(slug=slug, name=name, adapter=adapter, active=active)
        self.session.add(model)
        self.session.commit()
        return _insurer(model)

    def start_run(self, insurer_id: int, started_at: datetime) -> CollectionRun:
        model = CollectionRunModel(
            insurer_id=insurer_id,
            status=RunStatus.RUNNING.value,
            started_at=started_at,
        )
        self.session.add(model)
        self.session.commit()
        return _run(model)

    def finish_run(
        self,
        run_id: int,
        status: RunStatus,
        finished_at: datetime,
        items_found: int,
        new_count: int,
        resolved_count: int,
        error: str,
        evidence_path: str,
    ) -> None:
        model = self.session.get(CollectionRunModel, run_id)
        if model is None:
            return
        model.status = status.value
        model.finished_at = finished_at
        model.items_found = items_found
        model.new_count = new_count
        model.resolved_count = resolved_count
        model.error = error
        model.evidence_path = evidence_path
        self.session.commit()

    def set_insurer_run_times(
        self, insurer_id: int, last_run_at: datetime, last_success_at: datetime | None
    ) -> None:
        model = self.session.get(InsurerModel, insurer_id)
        if model is None:
            return
        model.last_run_at = last_run_at
        if last_success_at is not None:
            model.last_success_at = last_success_at
        self.session.commit()

    def load_snapshot(self, insurer_id: int) -> Snapshot:
        policies = self.session.scalars(
            select(PolicyModel).where(PolicyModel.insurer_id == insurer_id)
        ).all()
        policy_map = {
            (PendencyKind(model.kind), model.policy_number): _policy(model) for model in policies
        }

        rows = self.session.execute(
            select(PolicyModel, InstallmentModel, PendencyModel)
            .join(InstallmentModel, InstallmentModel.policy_id == PolicyModel.id)
            .join(PendencyModel, PendencyModel.installment_id == InstallmentModel.id)
            .where(PolicyModel.insurer_id == insurer_id)
        ).all()

        items: dict[tuple[PendencyKind, str, int, date], ExistingInstallment] = {}
        for policy_model, installment_model, pendency_model in rows:
            policy = _policy(policy_model)
            installment = _installment(installment_model)
            key = installment_key(
                PendencyKind(policy_model.kind),
                policy.policy_number,
                installment.number,
                installment.due_date,
            )
            items[key] = ExistingInstallment(
                kind=PendencyKind(policy_model.kind),
                policy_number=policy.policy_number,
                installment=installment,
                pendency=_pendency(pendency_model),
            )
        return Snapshot(policies=policy_map, items=items)

    def apply_diff(self, insurer_id: int, diff: DiffResult, collected_at: datetime) -> ApplyStats:
        reopened_keys = {
            installment_key(item.kind, item.policy_number, item.installment_number, item.due_date)
            for item in diff.reopened
        }
        discarded_keys = {
            installment_key(item.kind, item.policy_number, item.installment_number, item.due_date)
            for item in diff.discarded_reappeared
        }

        try:
            policies = {
                (PendencyKind(model.kind), model.policy_number): model
                for model in self.session.scalars(
                    select(PolicyModel).where(PolicyModel.insurer_id == insurer_id)
                )
            }

            for item in diff.incoming:
                policy_key = (item.kind, item.policy_number)
                policy_model = policies.get(policy_key)
                if policy_model is None:
                    policy_model = PolicyModel(
                        insurer_id=insurer_id,
                        kind=item.kind.value,
                        policy_number=item.policy_number,
                        insured_name=item.insured_name,
                        branch=item.branch,
                        producer=item.producer,
                    )
                    self.session.add(policy_model)
                    self.session.flush()
                    policies[policy_key] = policy_model
                else:
                    policy_model.kind = item.kind.value
                    policy_model.insured_name = item.insured_name
                    policy_model.branch = item.branch
                    policy_model.producer = item.producer

                installment_model = self.session.scalar(
                    select(InstallmentModel).where(
                        InstallmentModel.policy_id == policy_model.id,
                        InstallmentModel.number == item.installment_number,
                        InstallmentModel.due_date == item.due_date,
                    )
                )
                if installment_model is None:
                    installment_model = InstallmentModel(
                        policy_id=policy_model.id,
                        number=item.installment_number,
                        due_date=item.due_date,
                        amount_cents=item.amount_cents,
                        first_seen_at=collected_at,
                        last_seen_at=collected_at,
                        is_active=True,
                    )
                    self.session.add(installment_model)
                    self.session.flush()

                installment_model.amount_cents = item.amount_cents
                installment_model.boleto_url = item.boleto_url
                installment_model.boleto_code = item.boleto_code
                installment_model.external_id = item.external_id
                installment_model.alerts = item.alerts
                installment_model.payment_method = item.payment_method
                installment_model.adjusted_vigency = item.adjusted_vigency
                installment_model.insurer_status = item.insurer_status
                installment_model.is_active = True
                installment_model.last_seen_at = collected_at

                pendency_model = self.session.scalar(
                    select(PendencyModel).where(
                        PendencyModel.installment_id == installment_model.id
                    )
                )
                key = installment_key(
                    item.kind, item.policy_number, item.installment_number, item.due_date
                )

                if pendency_model is None:
                    pendency_model = PendencyModel(
                        installment_id=installment_model.id,
                        workflow_status=WorkflowStatus.DETECTADA.value,
                        deadline=item.deadline,
                        assigned_to=item.producer,
                        created_at=collected_at,
                        updated_at=collected_at,
                    )
                    self.session.add(pendency_model)
                    self.session.flush()
                    self._add_event(
                        pendency_model.id,
                        None,
                        WorkflowStatus.DETECTADA,
                        "Coleta inicial",
                        collected_at,
                    )
                elif key in reopened_keys:
                    old_status = WorkflowStatus(pendency_model.workflow_status)
                    pendency_model.workflow_status = WorkflowStatus.DETECTADA.value
                    pendency_model.updated_at = collected_at
                    if pendency_model.deadline is None:
                        pendency_model.deadline = item.deadline
                    self._add_event(
                        pendency_model.id,
                        old_status,
                        WorkflowStatus.DETECTADA,
                        "Reapareceu na coleta",
                        collected_at,
                    )
                elif key in discarded_keys:
                    status = WorkflowStatus(pendency_model.workflow_status)
                    self._add_event(
                        pendency_model.id,
                        status,
                        status,
                        "Reapareceu após descarte; revisar manualmente",
                        collected_at,
                    )
                else:
                    if pendency_model.deadline is None and item.deadline is not None:
                        pendency_model.deadline = item.deadline
                    if not pendency_model.assigned_to and item.producer:
                        pendency_model.assigned_to = item.producer

            for existing in diff.missing:
                if existing.installment.id is None or existing.pendency.id is None:
                    continue
                installment_model = self.session.get(InstallmentModel, existing.installment.id)
                if installment_model is None:
                    continue
                installment_model.is_active = False
                pendency_model = self.session.get(PendencyModel, existing.pendency.id)
                if pendency_model is None:
                    continue
                status = WorkflowStatus(pendency_model.workflow_status)
                if status.is_open:
                    pendency_model.workflow_status = WorkflowStatus.REGULARIZADA.value
                    pendency_model.updated_at = collected_at
                    self._add_event(
                        pendency_model.id,
                        status,
                        WorkflowStatus.REGULARIZADA,
                        f"Não consta na coleta de {collected_at:%d/%m/%Y}",
                        collected_at,
                    )

            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return ApplyStats(
            new_count=len(diff.new),
            resolved_count=diff.resolved_count,
        )

    def _add_event(
        self,
        pendency_id: int,
        from_status: WorkflowStatus | None,
        to_status: WorkflowStatus,
        note: str,
        created_at: datetime,
    ) -> None:
        self.session.add(
            PendencyEventModel(
                pendency_id=pendency_id,
                from_status=from_status.value if from_status else None,
                to_status=to_status.value,
                note=note,
                created_at=created_at,
            )
        )

    def list_pendencies(self, filters: PendencyFilters, today: date) -> list[PendencyView]:
        stmt = (
            select(PendencyModel, InstallmentModel, PolicyModel, InsurerModel)
            .join(InstallmentModel, InstallmentModel.id == PendencyModel.installment_id)
            .join(PolicyModel, PolicyModel.id == InstallmentModel.policy_id)
            .join(InsurerModel, InsurerModel.id == PolicyModel.insurer_id)
        )

        if filters.insurer_slug:
            stmt = stmt.where(InsurerModel.slug == filters.insurer_slug)

        if filters.kind:
            try:
                kind = PendencyKind(filters.kind)
            except ValueError:
                return []
            stmt = stmt.where(PolicyModel.kind == kind.value)

        if filters.status == OPEN_FILTER:
            stmt = stmt.where(PendencyModel.workflow_status.in_(OPEN_VALUES))
        elif filters.status == OVERDUE_FILTER:
            stmt = stmt.where(
                PendencyModel.workflow_status.in_(OPEN_VALUES),
                InstallmentModel.due_date < today,
            )
        elif filters.status:
            try:
                status = WorkflowStatus(filters.status)
            except ValueError:
                return []
            stmt = stmt.where(PendencyModel.workflow_status == status.value)

        if filters.q:
            term = f"%{filters.q.strip()}%"
            stmt = stmt.where(
                or_(
                    PolicyModel.insured_name.ilike(term),
                    PolicyModel.policy_number.ilike(term),
                    InsurerModel.name.ilike(term),
                )
            )

        stmt = stmt.order_by(InstallmentModel.due_date.asc(), PolicyModel.insured_name.asc()).limit(
            1000
        )

        rows = self.session.execute(stmt).all()
        return [
            _view(pendency, installment, policy, insurer, today)
            for pendency, installment, policy, insurer in rows
        ]

    def summary(self, today: date, stale_before: datetime) -> Summary:
        total_open = (
            self.session.scalar(
                select(func.count(PendencyModel.id))
                .join(InstallmentModel, InstallmentModel.id == PendencyModel.installment_id)
                .where(PendencyModel.workflow_status.in_(OPEN_VALUES))
            )
            or 0
        )
        due_soon = (
            self.session.scalar(
                select(func.count(PendencyModel.id))
                .join(InstallmentModel, InstallmentModel.id == PendencyModel.installment_id)
                .where(
                    PendencyModel.workflow_status.in_(OPEN_VALUES),
                    InstallmentModel.due_date >= today,
                    InstallmentModel.due_date <= today + timedelta(days=7),
                )
            )
            or 0
        )
        overdue = (
            self.session.scalar(
                select(func.count(PendencyModel.id))
                .join(InstallmentModel, InstallmentModel.id == PendencyModel.installment_id)
                .where(
                    PendencyModel.workflow_status.in_(OPEN_VALUES),
                    InstallmentModel.due_date < today,
                )
            )
            or 0
        )
        failed_insurers = (
            self.session.scalar(
                select(func.count(InsurerModel.id)).where(
                    InsurerModel.active.is_(True),
                    or_(
                        InsurerModel.last_success_at.is_(None),
                        InsurerModel.last_success_at < stale_before,
                    ),
                )
            )
            or 0
        )
        total_insurers = (
            self.session.scalar(
                select(func.count(InsurerModel.id)).where(InsurerModel.active.is_(True))
            )
            or 0
        )
        return Summary(
            total_open=int(total_open),
            due_soon=int(due_soon),
            overdue=int(overdue),
            failed_insurers=int(failed_insurers),
            total_insurers=int(total_insurers),
        )

    def _view_by_id(self, pendency_id: int, today: date):
        return self.session.execute(
            select(PendencyModel, InstallmentModel, PolicyModel, InsurerModel)
            .join(InstallmentModel, InstallmentModel.id == PendencyModel.installment_id)
            .join(PolicyModel, PolicyModel.id == InstallmentModel.policy_id)
            .join(InsurerModel, InsurerModel.id == PolicyModel.insurer_id)
            .where(PendencyModel.id == pendency_id)
        ).first()

    def get_pendency_detail(self, pendency_id: int, today: date) -> PendencyDetail | None:
        row = self._view_by_id(pendency_id, today)
        if row is None:
            return None
        pendency, installment, policy, insurer = row
        events = self.session.scalars(
            select(PendencyEventModel)
            .where(PendencyEventModel.pendency_id == pendency_id)
            .order_by(PendencyEventModel.created_at.desc(), PendencyEventModel.id.desc())
        ).all()
        return PendencyDetail(
            view=_view(pendency, installment, policy, insurer, today),
            notes=pendency.notes,
            events=tuple(_event(event) for event in events),
            installment_id=pendency.installment_id,
        )

    def update_pendency(
        self,
        pendency_id: int,
        update: PendencyUpdate,
        note: str,
        now: datetime,
        today: date,
    ) -> PendencyDetail | None:
        pendency = self.session.get(PendencyModel, pendency_id)
        if pendency is None:
            return None
        old_status = WorkflowStatus(pendency.workflow_status)
        changed = any(
            [
                old_status is not update.workflow_status,
                pendency.action != update.action,
                pendency.action_date != update.action_date,
                pendency.new_due_date != update.new_due_date,
                pendency.deadline != update.deadline,
                pendency.assigned_to != update.assigned_to,
                pendency.notes != update.notes,
            ]
        )
        pendency.workflow_status = update.workflow_status.value
        pendency.action = update.action
        pendency.action_date = update.action_date
        pendency.new_due_date = update.new_due_date
        pendency.deadline = update.deadline
        pendency.assigned_to = update.assigned_to
        pendency.notes = update.notes
        pendency.updated_at = now

        if old_status is not update.workflow_status:
            event_note = note or (
                f"Status alterado de {old_status.label} para {update.workflow_status.label}"
            )
            self._add_event(pendency.id, old_status, update.workflow_status, event_note, now)
        elif changed or note:
            self._add_event(
                pendency.id,
                old_status,
                update.workflow_status,
                note or "Tratamento atualizado",
                now,
            )

        self.session.commit()
        return self.get_pendency_detail(pendency_id, today)

    def update_status(
        self,
        pendency_id: int,
        status: WorkflowStatus,
        now: datetime,
        today: date,
    ) -> PendencyView | None:
        pendency = self.session.get(PendencyModel, pendency_id)
        if pendency is None:
            return None
        old_status = WorkflowStatus(pendency.workflow_status)
        if old_status is not status:
            pendency.workflow_status = status.value
            pendency.updated_at = now
            self._add_event(
                pendency.id,
                old_status,
                status,
                f"Status alterado de {old_status.label} para {status.label}",
                now,
            )
            self.session.commit()
        row = self._view_by_id(pendency_id, today)
        if row is None:
            return None
        pendency_model, installment, policy, insurer = row
        return _view(pendency_model, installment, policy, insurer, today)

    def mark_overdue(self, today: date, now: datetime) -> int:
        rows = self.session.execute(
            select(PendencyModel, InstallmentModel)
            .join(InstallmentModel, InstallmentModel.id == PendencyModel.installment_id)
            .where(
                PendencyModel.workflow_status.in_(OPEN_VALUES),
                InstallmentModel.due_date < today,
            )
        ).all()
        for pendency, _installment in rows:
            old_status = WorkflowStatus(pendency.workflow_status)
            pendency.workflow_status = WorkflowStatus.VENCIDA.value
            pendency.updated_at = now
            self._add_event(
                pendency.id,
                old_status,
                WorkflowStatus.VENCIDA,
                "Vencimento ultrapassado",
                now,
            )
        if rows:
            self.session.commit()
        return len(rows)

    def list_runs(self, limit: int = 20) -> list[RunView]:
        rows = self.session.execute(
            select(CollectionRunModel, InsurerModel)
            .join(InsurerModel, InsurerModel.id == CollectionRunModel.insurer_id)
            .order_by(CollectionRunModel.started_at.desc())
            .limit(limit)
        ).all()
        return [
            RunView(
                id=run.id,
                insurer_name=insurer.name,
                status=RunStatus(run.status),
                started_at=run.started_at,
                finished_at=run.finished_at,
                items_found=run.items_found,
                new_count=run.new_count,
                resolved_count=run.resolved_count,
                error=run.error,
                evidence_path=run.evidence_path,
            )
            for run, insurer in rows
        ]

    def list_insurer_health(self, stale_before: datetime) -> list[InsurerHealth]:
        insurers = self.session.scalars(select(InsurerModel).order_by(InsurerModel.name)).all()
        result: list[InsurerHealth] = []
        for insurer in insurers:
            last_run = self.session.scalar(
                select(CollectionRunModel)
                .where(CollectionRunModel.insurer_id == insurer.id)
                .order_by(CollectionRunModel.started_at.desc())
                .limit(1)
            )
            is_stale = insurer.last_success_at is None or insurer.last_success_at < stale_before
            result.append(
                InsurerHealth(
                    slug=insurer.slug,
                    name=insurer.name,
                    active=insurer.active,
                    last_run_at=insurer.last_run_at,
                    last_success_at=insurer.last_success_at,
                    is_stale=is_stale,
                    last_status=RunStatus(last_run.status) if last_run else None,
                    last_error=last_run.error if last_run else "",
                )
            )
        return result
