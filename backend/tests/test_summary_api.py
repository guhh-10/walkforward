import datetime as dt
from typing import Any

import httpx2
from fastapi.testclient import TestClient

from tests.conftest import CategoryIds

TXN_URL = "/api/transactions"
MONTHLY = "/api/summary/monthly"
TRENDS = "/api/summary/trends"


def add(
    client: TestClient,
    cat: CategoryIds,
    *,
    date: str,
    amount: float,
    type: str = "expense",
    category: str = "Groceries",
) -> httpx2.Response:
    r = client.post(
        TXN_URL,
        json={
            "amount": amount,
            "type": type,
            "date": date,
            "description": "test",
            "category_id": cat[type, category],
        },
    )
    assert r.status_code == 201, r.text
    return r


def first_of_month(offset: int) -> dt.date:
    """First day of the month `offset` months before the current one."""
    today = dt.date.today()
    index = today.year * 12 + (today.month - 1) - offset
    return dt.date(index // 12, index % 12 + 1, 1)


# ---------- monthly ----------
def test_monthly_summary_totals_and_breakdown(
    client: TestClient, cat: CategoryIds
) -> None:
    add(client, cat, date="2026-10-05", amount=5000, type="income", category="Salary")
    add(client, cat, date="2026-10-06", amount=30, category="Groceries")
    add(client, cat, date="2026-10-20", amount=10, category="Groceries")
    add(client, cat, date="2026-10-21", amount=60, category="Housing")

    body: dict[str, Any] = client.get(MONTHLY, params={"month": "2026-10"}).json()
    assert body["month"] == "2026-10"
    assert (body["income"], body["expense"], body["net"]) == (5000, 100, 4900)

    by_name = {c["name"]: c for c in body["by_category"]}
    assert by_name["Groceries"]["total"] == 40
    assert by_name["Groceries"]["pct"] == 40.0
    assert by_name["Housing"]["pct"] == 60.0
    assert by_name["Salary"]["pct"] == 100.0
    # Expense pcts sum to 100 on their own, independent of income.
    expense_pct = sum(c["pct"] for c in body["by_category"] if c["type"] == "expense")
    assert expense_pct == 100.0


def test_monthly_summary_respects_month_boundaries(
    client: TestClient, cat: CategoryIds
) -> None:
    add(client, cat, date="2026-09-30", amount=1)
    add(client, cat, date="2026-10-01", amount=2)
    add(client, cat, date="2026-10-31", amount=4)
    add(client, cat, date="2026-11-01", amount=8)

    body = client.get(MONTHLY, params={"month": "2026-10"}).json()
    assert body["expense"] == 6


def test_monthly_summary_december(client: TestClient, cat: CategoryIds) -> None:
    add(client, cat, date="2026-12-31", amount=7)
    add(client, cat, date="2027-01-01", amount=9)
    assert client.get(MONTHLY, params={"month": "2026-12"}).json()["expense"] == 7


def test_monthly_summary_empty_month(client: TestClient) -> None:
    body = client.get(MONTHLY, params={"month": "2020-01"}).json()
    assert body == {
        "month": "2020-01",
        "income": 0,
        "expense": 0,
        "net": 0,
        "by_category": [],
    }


def test_monthly_summary_defaults_to_current_month(client: TestClient) -> None:
    body = client.get(MONTHLY).json()
    assert body["month"] == dt.date.today().strftime("%Y-%m")


def test_monthly_summary_rejects_bad_month(client: TestClient) -> None:
    for bad in ("2026-13", "2026-1", "26-10", "abc", "2026-10-01", "0000-01"):
        r = client.get(MONTHLY, params={"month": bad})
        assert r.status_code == 422, bad
        assert r.json()["code"] == "VALIDATION_ERROR"


# ---------- trends ----------
def test_trends_defaults_to_twelve_months_oldest_first(client: TestClient) -> None:
    points = client.get(TRENDS).json()
    assert len(points) == 12
    months = [p["month"] for p in points]
    assert months == sorted(months)
    assert months[-1] == dt.date.today().strftime("%Y-%m")
    assert all(p["income"] == p["expense"] == p["net"] == 0 for p in points)


def test_trends_aggregate_and_zero_fill(client: TestClient, cat: CategoryIds) -> None:
    this_month = first_of_month(0).isoformat()
    two_ago = first_of_month(2).isoformat()
    add(client, cat, date=two_ago, amount=40)
    add(client, cat, date=this_month, amount=100, type="income", category="Salary")
    add(client, cat, date=this_month, amount=25)

    points = client.get(TRENDS, params={"months": 3}).json()
    assert [p["month"] for p in points] == [
        two_ago[:7],
        first_of_month(1).isoformat()[:7],
        this_month[:7],
    ]
    assert [(p["income"], p["expense"], p["net"]) for p in points] == [
        (0, 40, -40),
        (0, 0, 0),
        (100, 25, 75),
    ]


def test_trends_exclude_transactions_outside_window(
    client: TestClient, cat: CategoryIds
) -> None:
    add(client, cat, date=first_of_month(5).isoformat(), amount=999)
    points = client.get(TRENDS, params={"months": 3}).json()
    assert sum(p["expense"] for p in points) == 0


def test_trends_rejects_bad_months(client: TestClient) -> None:
    assert client.get(TRENDS, params={"months": 0}).status_code == 422
    assert client.get(TRENDS, params={"months": 61}).status_code == 422
