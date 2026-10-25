import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Transaction


def first_transaction_date(db: Session) -> dt.date | None:
    """The logging anchor: the earliest transaction of any type."""
    return db.scalar(select(func.min(Transaction.txn_date)))


def expense_totals_by_month(db: Session) -> dict[str, int]:
    """Expense cents per calendar month ('YYYY-MM'). Reads amounts and dates only."""
    month = func.strftime("%Y-%m", Transaction.txn_date)
    stmt = (
        select(month, func.sum(Transaction.amount_cents))
        .where(Transaction.type == "expense")
        .group_by(month)
    )
    return {m: int(total) for m, total in db.execute(stmt)}
