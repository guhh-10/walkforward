from typing import Any

import httpx2
from app.models import Transaction
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import CategoryIds

URL = "/api/transactions"


def payload(cat: CategoryIds, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "amount": 12.5,
        "type": "expense",
        "date": "2026-10-01",
        "description": "Lunch at warung",
        "category_id": cat["expense", "Groceries"],
    }
    body.update(over)
    return body


def post(client: TestClient, cat: CategoryIds, **over: Any) -> httpx2.Response:
    return client.post(URL, json=payload(cat, **over))


def create(client: TestClient, cat: CategoryIds, **over: Any) -> dict[str, Any]:
    r = post(client, cat, **over)
    assert r.status_code == 201, r.text
    return r.json()


# ---------- create ----------
def test_create_returns_transaction(client: TestClient, cat: CategoryIds) -> None:
    data = create(client, cat)
    assert data["amount"] == 12.5
    assert data["category_name"] == "Groceries"
    assert data["classification"] is None
    assert data["is_future"] is False


def test_amount_stored_as_integer_cents(
    client: TestClient, cat: CategoryIds, session_factory: sessionmaker[Session]
) -> None:
    data = create(client, cat, amount="19.99")
    with session_factory() as db:
        txn = db.get(Transaction, data["id"])
        assert txn is not None
        assert txn.amount_cents == 1999


def test_description_is_trimmed(client: TestClient, cat: CategoryIds) -> None:
    assert create(client, cat, description="  coffee  ")["description"] == "coffee"


def test_future_date_allowed_but_flagged(client: TestClient, cat: CategoryIds) -> None:
    assert create(client, cat, date="2999-01-01")["is_future"] is True


def test_create_rejects_non_positive_amount(
    client: TestClient, cat: CategoryIds
) -> None:
    for bad in (0, -5):
        r = post(client, cat, amount=bad)
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"


def test_create_rejects_more_than_two_decimals(
    client: TestClient, cat: CategoryIds
) -> None:
    assert post(client, cat, amount="1.005").status_code == 422


def test_create_rejects_bad_description(client: TestClient, cat: CategoryIds) -> None:
    assert post(client, cat, description="   ").status_code == 422
    assert post(client, cat, description="x" * 501).status_code == 422


def test_create_rejects_invalid_date_and_type(
    client: TestClient, cat: CategoryIds
) -> None:
    assert post(client, cat, date="2026-13-40").status_code == 422
    assert post(client, cat, type="transfer").status_code == 422


def test_category_type_mismatch_rejected(client: TestClient, cat: CategoryIds) -> None:
    r = post(client, cat, category_id=cat["income", "Salary"])
    assert r.status_code == 422
    assert r.json()["code"] == "CATEGORY_TYPE_MISMATCH"


def test_unknown_category_rejected(client: TestClient, cat: CategoryIds) -> None:
    r = post(client, cat, category_id=99999)
    assert r.status_code == 422
    assert r.json()["code"] == "CATEGORY_NOT_FOUND"


def test_category_required_without_model(client: TestClient, cat: CategoryIds) -> None:
    body = payload(cat)
    del body["category_id"]
    r = client.post(URL, json=body)
    assert r.status_code == 422
    assert r.json()["code"] == "CATEGORY_REQUIRED"


# ---------- read ----------
def test_get_detail_and_404(client: TestClient, cat: CategoryIds) -> None:
    data = create(client, cat)
    assert client.get(f"{URL}/{data['id']}").json()["id"] == data["id"]
    r = client.get(f"{URL}/9999")
    assert r.status_code == 404
    assert r.json() == {
        "detail": "Transaction 9999 not found.",
        "code": "TRANSACTION_NOT_FOUND",
    }


def test_list_pagination_and_ordering(client: TestClient, cat: CategoryIds) -> None:
    for day in range(1, 6):
        create(client, cat, date=f"2026-10-0{day}", description=f"item {day}")
    r = client.get(URL, params={"page": 1, "page_size": 2}).json()
    assert r["total"] == 5 and r["page"] == 1 and r["page_size"] == 2
    assert [i["description"] for i in r["items"]] == ["item 5", "item 4"]
    last = client.get(URL, params={"page": 3, "page_size": 2}).json()
    assert [i["description"] for i in last["items"]] == ["item 1"]


def test_list_rejects_bad_pagination(client: TestClient) -> None:
    assert client.get(URL, params={"page": 0}).status_code == 422
    assert client.get(URL, params={"page_size": 101}).status_code == 422


def test_filters(client: TestClient, cat: CategoryIds) -> None:
    create(client, cat, date="2026-09-10", description="Indomaret snacks")
    create(
        client,
        cat,
        date="2026-10-10",
        description="Gojek ride",
        category_id=cat["expense", "Transportation"],
    )
    create(
        client,
        cat,
        date="2026-10-15",
        type="income",
        amount=5000,
        description="October salary",
        category_id=cat["income", "Salary"],
    )

    def count(**params: Any) -> int:
        return client.get(URL, params=params).json()["total"]

    assert count(type="income") == 1
    assert count(category_id=cat["expense", "Transportation"]) == 1
    assert count(**{"from": "2026-10-01", "to": "2026-10-31"}) == 2
    assert count(**{"from": "2026-10-10", "to": "2026-10-10"}) == 1  # inclusive
    assert count(q="GOJEK") == 1  # case-insensitive
    assert count(q="zzz") == 0
    assert count(status="PREDICTED") == 0  # no classifications yet


def test_search_treats_wildcards_literally(
    client: TestClient, cat: CategoryIds
) -> None:
    create(client, cat, description="50% off sale")
    create(client, cat, description="plain item")
    assert client.get(URL, params={"q": "%"}).json()["total"] == 1


# ---------- update ----------
def test_update_replaces_fields(client: TestClient, cat: CategoryIds) -> None:
    data = create(client, cat)
    body = payload(
        cat,
        amount=99,
        description="Edited",
        category_id=cat["expense", "Shopping"],
    )
    r = client.put(f"{URL}/{data['id']}", json=body)
    assert r.status_code == 200
    out = r.json()
    assert out["amount"] == 99
    assert out["description"] == "Edited"
    assert out["category_name"] == "Shopping"


def test_update_can_change_type_with_matching_category(
    client: TestClient, cat: CategoryIds
) -> None:
    data = create(client, cat)
    body = payload(cat, type="income", category_id=cat["income", "Salary"])
    r = client.put(f"{URL}/{data['id']}", json=body)
    assert r.status_code == 200
    assert r.json()["type"] == "income"


def test_update_validates_category_and_404(
    client: TestClient, cat: CategoryIds
) -> None:
    data = create(client, cat)
    bad = client.put(
        f"{URL}/{data['id']}",
        json=payload(cat, category_id=cat["income", "Salary"]),
    )
    assert bad.status_code == 422
    unchanged = client.get(f"{URL}/{data['id']}").json()
    assert unchanged["category_name"] == "Groceries"
    assert client.put(f"{URL}/9999", json=payload(cat)).status_code == 404


# ---------- delete ----------
def test_delete(client: TestClient, cat: CategoryIds) -> None:
    data = create(client, cat)
    assert client.delete(f"{URL}/{data['id']}").status_code == 204
    assert client.get(f"{URL}/{data['id']}").status_code == 404
    assert client.delete(f"{URL}/{data['id']}").status_code == 404
