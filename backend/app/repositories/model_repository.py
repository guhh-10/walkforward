from sqlalchemy import select, update
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


def next_version_tag(db: Session) -> str:
    """'v1' for the first model, then one more than the highest existing 'vN'."""
    numbers = [
        int(tag[1:])
        for tag in db.scalars(select(ModelVersion.version_tag))
        if tag.startswith("v") and tag[1:].isdigit()
    ]
    return f"v{max(numbers, default=0) + 1}"


def deactivate_all(db: Session) -> None:
    db.execute(update(ModelVersion).values(is_active=False))


def add(db: Session, version: ModelVersion) -> ModelVersion:
    db.add(version)
    db.flush()
    return version
