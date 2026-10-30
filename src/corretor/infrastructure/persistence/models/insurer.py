from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, utcnow

if TYPE_CHECKING:
    from .collection_run import CollectionRunModel
    from .policy import PolicyModel


class InsurerModel(Base):
    __tablename__ = "insurers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    adapter: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    policies: Mapped[list[PolicyModel]] = relationship(
        back_populates="insurer", cascade="all, delete-orphan"
    )
    runs: Mapped[list[CollectionRunModel]] = relationship(
        back_populates="insurer", cascade="all, delete-orphan"
    )
