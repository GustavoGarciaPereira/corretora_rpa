from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .installment import InstallmentModel
    from .insurer import InsurerModel


class PolicyModel(Base):
    __tablename__ = "policies"
    __table_args__ = (
        UniqueConstraint(
            "insurer_id", "kind", "policy_number", name="uq_policy_insurer_kind_number"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    insurer_id: Mapped[int] = mapped_column(ForeignKey("insurers.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), default="PARCELA")
    policy_number: Mapped[str] = mapped_column(String(120))
    insured_name: Mapped[str] = mapped_column(String(200))
    branch: Mapped[str] = mapped_column(String(120), default="")
    producer: Mapped[str] = mapped_column(String(120), default="")

    insurer: Mapped[InsurerModel] = relationship(back_populates="policies")
    installments: Mapped[list[InstallmentModel]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )
