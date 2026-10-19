from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.classification import Classification

from app.database.connection import Base


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        CheckConstraint(
            "amount_cents > 0",
            name="ck_transaction_amount_positive",
        ),
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_transaction_type",
        ),
        Index("idx_txn_type_date", "type", "txn_date"),
        Index("idx_txn_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    amount_cents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    type: Mapped[str] = mapped_column(String, nullable=False)
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    category: Mapped["Category"] = relationship(
        back_populates="transactions"
    )

    classification: Mapped["Classification | None"] = relationship(
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
