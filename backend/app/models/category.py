from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Category(Base):
    __tablename__ = "categories"

    __table_args__ = (
        UniqueConstraint("name", "type", name="uq_category_name_type"),
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="ck_category_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)

    is_default: Mapped[bool] = mapped_column(
        default=False,
        server_default=text("0"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="category"
    )
