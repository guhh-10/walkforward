from sqlalchemy.orm import Session

from app.models import Classification


def add(db: Session, classification: Classification) -> Classification:
    db.add(classification)
    db.flush()
    return classification
