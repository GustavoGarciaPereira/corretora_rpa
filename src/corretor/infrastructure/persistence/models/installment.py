from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .pendency import PendencyModel
    from .policy import PolicyModel


class InstallmentModel(Base):
    __tablename__ = "installments"
    __table_args__ = (
        UniqueConstraint(
            "policy_id", "number", "due_date", name="uq_installment_policy_number_due"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    boleto_url: Mapped[str] = mapped_column(Text, default="")
    boleto_code: Mapped[str] = mapped_column(String(120), default="")
    external_id: Mapped[str] = mapped_column(String(120), default="")
    alerts: Mapped[str] = mapped_column(Text, default="")
    payment_method: Mapped[str] = mapped_column(String(80), default="")
    adjusted_vigency: Mapped[str] = mapped_column(String(120), default="")
    insurer_status: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime)

    policy: Mapped[PolicyModel] = relationship(back_populates="installments")
    pendency: Mapped[PendencyModel | None] = relationship(
        back_populates="installment", uselist=False, cascade="all, delete-orphan"
    )
