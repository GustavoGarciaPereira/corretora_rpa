from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from corretor.domain.enums import RunStatus

from .base import Base

if TYPE_CHECKING:
    from .insurer import InsurerModel


class CollectionRunModel(Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insurer_id: Mapped[int] = mapped_column(ForeignKey("insurers.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default=RunStatus.RUNNING.value)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    evidence_path: Mapped[str] = mapped_column(String(500), default="")

    insurer: Mapped[InsurerModel] = relationship(back_populates="runs")
