from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from corretor.domain.enums import WorkflowStatus

from .base import Base, utcnow

if TYPE_CHECKING:
    from .installment import InstallmentModel
    from .pendency_event import PendencyEventModel


class PendencyModel(Base):
    __tablename__ = "pendencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installment_id: Mapped[int] = mapped_column(
        ForeignKey("installments.id"), unique=True, index=True
    )
    workflow_status: Mapped[str] = mapped_column(
        String(32), default=WorkflowStatus.DETECTADA.value, index=True
    )
    action: Mapped[str] = mapped_column(Text, default="")
    new_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_to: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    installment: Mapped[InstallmentModel] = relationship(back_populates="pendency")
    events: Mapped[list[PendencyEventModel]] = relationship(
        back_populates="pendency", cascade="all, delete-orphan"
    )
