from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.model_version import ModelVersion
    from app.models.transaction import Transaction

from app.database.connection import Base


class Classification(Base):
    __tablename__ = "classifications"

    __table_args__ = (
        UniqueConstraint(
            "transaction_id",
            name="uq_classification_transaction",
        ),
        CheckConstraint(
            "predicted_confidence BETWEEN 0 AND 1",
            name="ck_classification_confidence",
        ),
        CheckConstraint(
            "status IN ('PREDICTED', 'CONFIRMED', 'MANUALLY_CORRECTED')",
            name="ck_classification_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
    )

    model_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_versions.id"),
        nullable=True,
    )

    predicted_category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    predicted_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String,
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

    transaction: Mapped["Transaction"] = relationship(back_populates="classification")

    model_version: Mapped["ModelVersion | None"] = relationship(
        back_populates="classifications"
    )

    predicted_category: Mapped["Category"] = relationship()
