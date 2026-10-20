import datetime as dt
from dataclasses import dataclass
from typing import Any, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models import Classification, Transaction

_S = TypeVar("_S", bound=Select[Any])


@dataclass(frozen=True)
class TransactionFilters:
    date_from: dt.date | None = None
    date_to: dt.date | None = None
    type: str | None = None
    category_id: int | None = None
    q: str | None = None
    status: str | None = None


def _apply_filters(stmt: _S, f: TransactionFilters) -> _S:
    if f.date_from is not None:
        stmt = stmt.where(Transaction.txn_date >= f.date_from)
    if f.date_to is not None:
        stmt = stmt.where(Transaction.txn_date <= f.date_to)
    if f.type is not None:
        stmt = stmt.where(Transaction.type == f.type)
    if f.category_id is not None:
        stmt = stmt.where(Transaction.category_id == f.category_id)
    if f.q:
        stmt = stmt.where(Transaction.description.icontains(f.q, autoescape=True))
    if f.status is not None:
        has_status = Transaction.classification.has(Classification.status == f.status)
        stmt = stmt.where(has_status)
    return stmt


def add(db: Session, txn: Transaction) -> Transaction:
    db.add(txn)
    db.flush()
    return txn


def get(db: Session, txn_id: int) -> Transaction | None:
    stmt = (
        select(Transaction)
        .options(joinedload(Transaction.category))
        .where(Transaction.id == txn_id)
    )
    return db.scalars(stmt).unique().one_or_none()


def list_page(
    db: Session, filters: TransactionFilters, page: int, page_size: int
) -> tuple[list[Transaction], int]:
    total = db.scalar(_apply_filters(select(func.count(Transaction.id)), filters)) or 0
    stmt = (
        _apply_filters(select(Transaction), filters)
        .options(joinedload(Transaction.category))
        .order_by(Transaction.txn_date.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(stmt).unique()), total


def delete(db: Session, txn: Transaction) -> None:
    db.delete(txn)
    db.flush()
