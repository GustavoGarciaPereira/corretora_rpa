from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow

if TYPE_CHECKING:
    from .pendency import PendencyModel


class PendencyEventModel(Base):
    __tablename__ = "pendency_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pendency_id: Mapped[int] = mapped_column(ForeignKey("pendencies.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    pendency: Mapped[PendencyModel] = relationship(back_populates="events")
