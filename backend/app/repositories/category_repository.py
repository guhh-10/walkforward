from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Classification, Transaction


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)


def list_all(db: Session, category_type: str | None = None) -> list[Category]:
    stmt = select(Category).order_by(Category.type, Category.name)
    if category_type is not None:
        stmt = stmt.where(Category.type == category_type)
    return list(db.scalars(stmt))


def find_by_name_and_type(
    db: Session, name: str, category_type: str
) -> Category | None:
    """Case-insensitive lookup within one type."""
    stmt = select(Category).where(
        func.lower(Category.name) == name.lower(),
        Category.type == category_type,
    )
    return db.scalars(stmt).first()


def add(db: Session, category: Category) -> Category:
    db.add(category)
    db.flush()
    return category


def delete(db: Session, category: Category) -> None:
    db.delete(category)
    db.flush()


def count_transactions(db: Session, category_id: int) -> int:
    stmt = select(func.count(Transaction.id)).where(
        Transaction.category_id == category_id
    )
    return db.scalar(stmt) or 0


def count_classification_refs(db: Session, category_id: int) -> int:
    """Classifications whose stored prediction points at this category."""
    stmt = select(func.count(Classification.id)).where(
        Classification.predicted_category_id == category_id
    )
    return db.scalar(stmt) or 0
