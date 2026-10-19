from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    version_tag: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
    )

    algorithm: Mapped[str] = mapped_column(String, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False)

    train_metrics_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    artifact_path: Mapped[str] = mapped_column(String, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )

    classifications: Mapped[list["Classification"]] = relationship(
        back_populates="model_version"
    )
