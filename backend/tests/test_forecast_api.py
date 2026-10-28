import datetime as dt
from typing import Any

import httpx2
from app.ml.months import month_of, next_month
from fastapi.testclient import TestClient

from tests.conftest import CategoryIds

URL = "/api/forecasts"
TXN = "/api/transactions"


def month_start(months_ago: int) -> dt.date:
    today = dt.date.today()
    index = today.year * 12 + (today.month - 1) - months_ago
    return dt.date(index // 12, index % 12 + 1, 1)


def spend(
    client: TestClient,
    cat: CategoryIds,
    months_ago: int,
    amount: float,
    category: str = "Groceries",
) -> None:
    r = client.post(
        TXN,
        json={
            "amount": amount,
            "type": "expense",
            "date": month_start(months_ago).isoformat(),
            "description": "test",
            "category_id": cat["expense", category],
        },
    )
    assert r.status_code == 201, r.text


def seed_months(client: TestClient, cat: CategoryIds, n: int) -> None:
    """One expense in each of the last n complete months, with some variation."""
    for months_ago in range(n, 0, -1):
        spend(client, cat, months_ago, 1000 + 40 * ((months_ago * 7) % 5))


def forecast(client: TestClient) -> httpx2.Response:
    return client.post(URL)


def assert_ordered(body: dict[str, Any]) -> None:
    assert 0 <= body["optimistic"] <= body["baseline"] <= body["conservative"]


# ---------- not enough data ----------
def test_empty_database_is_insufficient(client: TestClient) -> None:
    r = forecast(client)
    assert r.status_code == 409
    assert r.json()["code"] == "INSUFFICIENT_DATA"


def test_two_complete_months_are_insufficient(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 2)
    assert forecast(client).status_code == 409


def test_current_month_alone_does_not_count(
    client: TestClient, cat: CategoryIds
) -> None:
    for months_ago in (0, 0, 0):
        spend(client, cat, months_ago, 100)
    assert forecast(client).status_code == 409


# ---------- degraded tier: 3-5 months ----------
def test_three_to_five_months_use_naive_and_ma_only_with_a_warning(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 4)
    r = forecast(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["backtest"]["per_model"]) == {"naive", "ma3"}
    assert body["reliability"] == "low"
    assert body["method"] == "t_approximation"
    assert body["warning"] and "4 months" in body["warning"]
    assert body["history_months"] == 4
    assert_ordered(body)


# ---------- full tier ----------
def test_six_or_more_months_add_ses_and_name_the_selected_model(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 12)
    body = forecast(client).json()
    assert set(body["backtest"]["per_model"]) == {"naive", "ma3", "ses"}
    assert body["selected_model"] in body["backtest"]["per_model"]
    assert body["history_months"] == 12
    assert body["history_start"] == month_of(month_start(12))
    assert body["backtest"]["residuals_used"] == 11
    assert body["reliability"] == "medium"
    assert body["method"] == "empirical_quantile"
    assert body["warning"] is None
    assert_ordered(body)


def test_target_is_the_month_after_the_current_one(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 6)
    target = forecast(client).json()["target_month"]
    assert target == next_month(month_of(dt.date.today()))


def test_a_long_history_is_high_reliability(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 33)
    body = forecast(client).json()
    assert body["reliability"] == "high"
    assert body["backtest"]["residuals_used"] == 32
    assert_ordered(body)


def test_backtest_table_has_a_row_per_model(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 8)
    per_model = forecast(client).json()["backtest"]["per_model"]
    for metrics in per_model.values():
        assert metrics["mae"] >= 0
        assert metrics["rmse"] >= metrics["mae"] - 1e-9
        assert metrics["mape_excluded"] == 0


def test_zero_spending_months_inside_the_history_are_real_zeros(
    client: TestClient, cat: CategoryIds
) -> None:
    for months_ago in (8, 7, 4, 2):  # gaps at 6, 5, 3 are zero-spend months
        spend(client, cat, months_ago, 500)
    body = forecast(client).json()
    assert body["history_months"] == 8
    assert_ordered(body)


# ---------- independence from classification ----------
def move_all_to(client: TestClient, cat: CategoryIds, category: str) -> None:
    """Re-categorise every transaction through the public API."""
    page = client.get(TXN, params={"page_size": 100}).json()
    for item in page["items"]:
        body: dict[str, Any] = {
            "amount": item["amount"],
            "type": item["type"],
            "date": item["date"],
            "description": item["description"],
            "category_id": cat["expense", category],
        }
        r = client.put(f"{TXN}/{item['id']}", json=body)
        assert r.status_code == 200, r.text


def test_forecast_ignores_which_category_an_expense_has(
    client: TestClient, cat: CategoryIds
) -> None:
    seed_months(client, cat, 8)
    before = forecast(client).json()
    move_all_to(client, cat, "Shopping")  # same totals, different categories
    assert forecast(client).json() == before
