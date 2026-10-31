"""Database tests: constraints and indexes the schema relies on.

These assert the guarantees SQLite itself enforces, independent of any service
or API layer: the app must never be the only thing standing between the data
and an inconsistent row.
"""

import datetime as dt

import pytest
from app.models import Category, Classification, Transaction
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import CategoryIds


def _txn(category_id: int) -> Transaction:
    return Transaction(
        amount_cents=100,
        type="expense",
        txn_date=dt.date(2026, 1, 15),
        description="test",
        category_id=category_id,
    )


# ---------- UNIQUE(name, type) ----------
def test_category_name_is_unique_within_a_type(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        db.add(Category(name="Custom", type="expense"))
        db.commit()
        db.add(Category(name="Custom", type="expense"))
        with pytest.raises(IntegrityError):
            db.commit()


def test_same_category_name_is_allowed_across_types(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        db.add(Category(name="Bonus", type="expense"))
        db.add(Category(name="Bonus", type="income"))
        db.commit()  # no error: the pair, not the name alone, is unique


# ---------- foreign keys ----------
def test_a_transaction_must_reference_a_real_category(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        db.add(_txn(category_id=999_999))
        with pytest.raises(IntegrityError):
            db.commit()


def test_a_classification_must_reference_a_real_transaction(
    session_factory: sessionmaker[Session], cat: CategoryIds
) -> None:
    with session_factory() as db:
        db.add(
            Classification(
                transaction_id=999_999,
                predicted_category_id=cat["expense", "Groceries"],
                predicted_confidence=0.5,
                status="PREDICTED",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


# ---------- UNIQUE(transaction_id) on classifications ----------
def test_a_transaction_has_at_most_one_classification(
    session_factory: sessionmaker[Session], cat: CategoryIds
) -> None:
    groceries = cat["expense", "Groceries"]
    with session_factory() as db:
        txn = _txn(groceries)
        db.add(txn)
        db.commit()
        db.add(
            Classification(
                transaction_id=txn.id,
                predicted_category_id=groceries,
                predicted_confidence=0.5,
                status="PREDICTED",
            )
        )
        db.commit()
        db.add(
            Classification(
                transaction_id=txn.id,
                predicted_category_id=groceries,
                predicted_confidence=0.9,
                status="CONFIRMED",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()


def test_deleting_a_transaction_cascades_to_its_classification(
    session_factory: sessionmaker[Session], cat: CategoryIds
) -> None:
    groceries = cat["expense", "Groceries"]
    with session_factory() as db:
        txn = _txn(groceries)
        db.add(txn)
        db.commit()
        db.add(
            Classification(
                transaction_id=txn.id,
                predicted_category_id=groceries,
                predicted_confidence=0.5,
                status="PREDICTED",
            )
        )
        db.commit()

        db.delete(txn)
        db.commit()
        assert db.scalars(select(Classification)).all() == []


# ---------- check constraints ----------
def test_amount_must_be_positive(
    session_factory: sessionmaker[Session], cat: CategoryIds
) -> None:
    with session_factory() as db:
        txn = _txn(cat["expense", "Groceries"])
        txn.amount_cents = 0
        db.add(txn)
        with pytest.raises(IntegrityError):
            db.commit()


# ---------- index smoke test ----------
def test_expected_transaction_indexes_exist(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        inspector = inspect(db.get_bind())
        indexes = {index["name"] for index in inspector.get_indexes("transactions")}
    assert {"idx_txn_type_date", "idx_txn_category"} <= indexes
