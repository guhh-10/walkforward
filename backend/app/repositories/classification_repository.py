from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Classification, Transaction


def add(db: Session, classification: Classification) -> Classification:
    db.add(classification)
    db.flush()
    return classification


REVIEWED_STATUSES = ("CONFIRMED", "MANUALLY_CORRECTED")


@dataclass(frozen=True)
class TrainingRow:
    description: str
    category_id: int  # the final category (what the user settled on)
    type: str


def reviewed_training_rows(db: Session) -> list[TrainingRow]:
    """Transactions whose final category a person chose or confirmed, oldest first.

    Unreviewed (PREDICTED) rows are excluded so the model never trains on its own
    guesses. Transactions with no classification row are included: their category
    was picked by the user before any model existed, which is also how the very
    first model gets its training data.
    """
    stmt = (
        select(Transaction.description, Transaction.category_id, Transaction.type)
        .outerjoin(Classification, Classification.transaction_id == Transaction.id)
        .where(
            or_(
                Classification.id.is_(None),
                Classification.status.in_(REVIEWED_STATUSES),
            )
        )
        .order_by(Transaction.txn_date, Transaction.id)
    )
    return [
        TrainingRow(description=d, category_id=c, type=t)
        for d, c, t in db.execute(stmt)
    ]
