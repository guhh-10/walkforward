import datetime as dt
from typing import Any

import pytest
from app.ml.forecasting import MonthlySeries, build_monthly_series
from app.models import Classification
from app.services import series_service
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import CategoryIds


# ---------- pure builder ----------
def test_groups_totals_by_month_in_order() -> None:
    totals = {"2026-01": 100, "2026-02": 250, "2026-03": 75}
    series = build_monthly_series(totals, dt.date(2026, 1, 10), "2026-03")
    assert series.months == ("2026-01", "2026-02", "2026-03")
    assert series.values == (100, 250, 75)


def test_zero_fills_empty_months_after_anchor() -> None:
    totals = {"2026-01": 100, "2026-04": 50}
    series = build_monthly_series(totals, dt.date(2026, 1, 1), "2026-04")
    assert series.values == (100, 0, 0, 50)


def test_excludes_months_before_anchor() -> None:
    totals = {"2025-11": 999, "2026-01": 100}
    series = build_monthly_series(totals, dt.date(2026, 1, 20), "2026-02")
    assert series.months == ("2026-01", "2026-02")
    assert series.values == (100, 0)  # pre-anchor 999 ignored, not zero-filled


def test_anchor_month_is_included_even_when_logging_started_mid_month() -> None:
    series = build_monthly_series({"2026-03": 10}, dt.date(2026, 3, 28), "2026-03")
    assert series.months == ("2026-03",)


def test_ignores_totals_after_end_month() -> None:
    totals = {"2026-01": 100, "2026-02": 500}
    series = build_monthly_series(totals, dt.date(2026, 1, 1), "2026-01")
    assert series.values == (100,)


def test_anchor_after_end_month_gives_empty_series() -> None:
    series = build_monthly_series({}, dt.date(2026, 10, 5), "2026-09")
    assert len(series) == 0
    assert series.anchor_month is None


def test_series_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        MonthlySeries(months=("2026-01",), values=(1, 2))


# ---------- DB-backed ----------
def add(
    client: TestClient,
    cat: CategoryIds,
    *,
    date: str,
    amount: float,
    type: str = "expense",
    category: str = "Groceries",
) -> None:
    body: dict[str, Any] = {
        "amount": amount,
        "type": type,
        "date": date,
        "description": "test",
        "category_id": cat[type, category],
    }
    assert client.post("/api/transactions", json=body).status_code == 201


def test_expense_series_sums_expenses_only_and_zero_fills(
    client: TestClient, cat: CategoryIds, session_factory: sessionmaker[Session]
) -> None:
    add(client, cat, date="2026-07-05", amount=10)
    add(client, cat, date="2026-07-20", amount=5.5)
    add(client, cat, date="2026-07-25", amount=999, type="income", category="Salary")
    add(client, cat, date="2026-09-02", amount=20, category="Housing")

    with session_factory() as db:
        series = series_service.expense_series(db, dt.date(2026, 10, 22))

    assert series.months == ("2026-07", "2026-08", "2026-09")
    assert series.values == (1550, 0, 2000)  # cents; income excluded; Oct not complete


def test_anchor_is_the_first_transaction_of_any_type(
    client: TestClient, cat: CategoryIds, session_factory: sessionmaker[Session]
) -> None:
    add(client, cat, date="2026-06-15", amount=100, type="income", category="Salary")
    add(client, cat, date="2026-08-03", amount=30)

    with session_factory() as db:
        series = series_service.expense_series(db, dt.date(2026, 10, 1))

    assert series.months[0] == "2026-06"
    assert series.values == (0, 0, 3000, 0)  # Jun, Jul zeros are real; Sep is zero


def test_expense_series_is_empty_without_transactions(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as db:
        assert len(series_service.expense_series(db, dt.date(2026, 10, 22))) == 0


def test_current_month_is_excluded_as_incomplete(
    client: TestClient, cat: CategoryIds, session_factory: sessionmaker[Session]
) -> None:
    add(client, cat, date="2026-10-01", amount=50)
    with session_factory() as db:
        assert len(series_service.expense_series(db, dt.date(2026, 10, 22))) == 0


def test_series_ignores_classification_rows(
    client: TestClient, cat: CategoryIds, session_factory: sessionmaker[Session]
) -> None:
    add(client, cat, date="2026-08-05", amount=10)
    with session_factory() as db:
        before = series_service.expense_series(db, dt.date(2026, 10, 22))

    with session_factory() as db:
        txn_id = 1
        db.add(
            Classification(
                transaction_id=txn_id,
                predicted_category_id=cat["expense", "Shopping"],
                predicted_confidence=0.1,
                status="PREDICTED",
            )
        )
        db.commit()
    with session_factory() as db:
        after = series_service.expense_series(db, dt.date(2026, 10, 22))

    assert before == after
