from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelVersion


def get_active(db: Session) -> ModelVersion | None:
    stmt = (
        select(ModelVersion)
        .where(ModelVersion.is_active.is_(True))
        .order_by(ModelVersion.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()
