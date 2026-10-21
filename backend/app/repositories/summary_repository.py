import datetime as dt
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Transaction


@dataclass(frozen=True)
class CategoryTotal:
    category_id: int
    name: str
    type: str
    total_cents: int


@dataclass(frozen=True)
class MonthTypeTotal:
    month: str  # YYYY-MM
    type: str
    total_cents: int


def category_totals(db: Session, start: dt.date, end: dt.date) -> list[CategoryTotal]:
    """Per-category sums for start <= txn_date < end (final categories only)."""
    stmt = (
        select(
            Category.id,
            Category.name,
            Category.type,
            func.sum(Transaction.amount_cents),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(Transaction.txn_date >= start, Transaction.txn_date < end)
        .group_by(Category.id, Category.name, Category.type)
    )
    return [
        CategoryTotal(category_id=cid, name=name, type=ctype, total_cents=int(total))
        for cid, name, ctype, total in db.execute(stmt)
    ]


def month_type_totals(
    db: Session, start: dt.date, end: dt.date
) -> list[MonthTypeTotal]:
    """Per (calendar month, type) sums for start <= txn_date < end."""
    month = func.strftime("%Y-%m", Transaction.txn_date)
    stmt = (
        select(month, Transaction.type, func.sum(Transaction.amount_cents))
        .where(Transaction.txn_date >= start, Transaction.txn_date < end)
        .group_by(month, Transaction.type)
    )
    return [
        MonthTypeTotal(month=m, type=ttype, total_cents=int(total))
        for m, ttype, total in db.execute(stmt)
    ]
