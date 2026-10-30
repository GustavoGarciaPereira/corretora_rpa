from __future__ import annotations

from datetime import date

from corretor.domain.entities import AdapterManifest, RawInstallment


def sample_items() -> list[RawInstallment]:
    """Dados fictícios, com datas fixas para a coleta ser idempotente."""
    return [
        RawInstallment(
            policy_number="000123-01/2026",
            insured_name="Maria Oliveira",
            branch="VIDA GRUPO",
            installment_number=12,
            due_date=date(2026, 10, 29),
            amount_cents=45_000,
            producer="Beto",
            boleto_code="000123450000012",
            external_id="demo-000123-12",
            deadline=date(2026, 11, 5),
        ),
        RawInstallment(
            policy_number="000123-01/2026",
            insured_name="Maria Oliveira",
            branch="VIDA GRUPO",
            installment_number=13,
            due_date=date(2026, 11, 29),
            amount_cents=45_000,
            producer="Beto",
            external_id="demo-000123-13",
        ),
        RawInstallment(
            policy_number="000456-01/2026",
            insured_name="João Santos",
            branch="AUTO",
            installment_number=4,
            due_date=date(2026, 11, 2),
            amount_cents=89_000,
            producer="Cássia",
            boleto_code="000456890000004",
            external_id="demo-000456-4",
            deadline=date(2026, 11, 9),
            alerts="Com crítica",
        ),
        RawInstallment(
            policy_number="000789-01/2026",
            insured_name="Transportes Alfa Ltda",
            branch="EMPRESARIAL",
            installment_number=7,
            due_date=date(2026, 11, 7),
            amount_cents=125_000,
            producer="Beto",
            external_id="demo-000789-7",
        ),
        RawInstallment(
            policy_number="000999-01/2026",
            insured_name="Ana Beatriz",
            branch="SAÚDE",
            installment_number=2,
            due_date=date(2026, 12, 4),
            amount_cents=62_000,
            producer="Cássia",
            external_id="demo-000999-2",
        ),
    ]


class DemoAdapter:
    def __init__(
        self,
        manifest: AdapterManifest,
        items: list[RawInstallment] | None = None,
    ) -> None:
        self.manifest = manifest
        self._items = items

    def fetch_pending(self) -> list[RawInstallment]:
        return list(self._items if self._items is not None else sample_items())
