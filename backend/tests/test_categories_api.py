from typing import Any

import httpx2
from app.database.seed import DEFAULT_CATEGORIES
from app.models import Classification
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import CategoryIds

URL = "/api/categories"
TXN_URL = "/api/transactions"


def post(client: TestClient, **body: Any) -> httpx2.Response:
    return client.post(URL, json=body)


def create_txn(client: TestClient, category_id: int) -> dict[str, Any]:
    r = client.post(
        TXN_URL,
        json={
            "amount": 10,
            "type": "expense",
            "date": "2026-10-01",
            "description": "something",
            "category_id": category_id,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# ---------- list ----------
def test_list_returns_seeded_categories(client: TestClient) -> None:
    items = client.get(URL).json()
    assert len(items) == sum(len(v) for v in DEFAULT_CATEGORIES.values())
    assert all(i["is_default"] for i in items)


def test_list_filters_by_type(client: TestClient) -> None:
    income = client.get(URL, params={"type": "income"}).json()
    assert {i["type"] for i in income} == {"income"}
    assert len(income) == len(DEFAULT_CATEGORIES["income"])
    assert client.get(URL, params={"type": "bogus"}).status_code == 422


# ---------- create ----------
def test_create_custom_category(client: TestClient) -> None:
    r = post(client, name="  Pets  ", type="expense")
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Pets"
    assert body["is_default"] is False
    names = [c["name"] for c in client.get(URL, params={"type": "expense"}).json()]
    assert "Pets" in names


def test_duplicate_name_and_type_conflicts(client: TestClient) -> None:
    r = post(client, name="Groceries", type="expense")
    assert r.status_code == 409
    assert r.json()["code"] == "CATEGORY_EXISTS"


def test_duplicate_check_ignores_case(client: TestClient) -> None:
    assert post(client, name="groceries", type="expense").status_code == 409


def test_same_name_allowed_across_types(client: TestClient) -> None:
    assert post(client, name="Gifts", type="expense").status_code == 201
    assert post(client, name="Gifts", type="income").status_code == 201


def test_create_validation(client: TestClient) -> None:
    assert post(client, name="   ", type="expense").status_code == 422
    assert post(client, name="x" * 51, type="expense").status_code == 422
    assert post(client, name="Valid", type="transfer").status_code == 422
    assert client.post(URL, json={"type": "expense"}).status_code == 422


def test_custom_category_usable_in_transaction(client: TestClient) -> None:
    new_id = post(client, name="Pets", type="expense").json()["id"]
    assert create_txn(client, new_id)["category_name"] == "Pets"


# ---------- delete ----------
def test_delete_unused_category(client: TestClient) -> None:
    new_id = post(client, name="Pets", type="expense").json()["id"]
    assert client.delete(f"{URL}/{new_id}").status_code == 204
    names = [c["name"] for c in client.get(URL).json()]
    assert "Pets" not in names


def test_delete_missing_category_404(client: TestClient) -> None:
    r = client.delete(f"{URL}/9999")
    assert r.status_code == 404
    assert r.json()["code"] == "CATEGORY_NOT_FOUND"


def test_delete_rejected_while_transactions_reference_it(
    client: TestClient, cat: CategoryIds
) -> None:
    groceries = cat["expense", "Groceries"]
    txn = create_txn(client, groceries)

    r = client.delete(f"{URL}/{groceries}")
    assert r.status_code == 409
    assert r.json()["code"] == "CATEGORY_IN_USE"

    # Explicit reassignment (here: removing the transaction) unblocks deletion.
    assert client.delete(f"{TXN_URL}/{txn['id']}").status_code == 204
    assert client.delete(f"{URL}/{groceries}").status_code == 204


def test_delete_rejected_while_predictions_reference_it(
    client: TestClient, cat: CategoryIds, session_factory: sessionmaker[Session]
) -> None:
    txn = create_txn(client, cat["expense", "Groceries"])
    shopping = cat["expense", "Shopping"]
    with session_factory() as db:
        db.add(
            Classification(
                transaction_id=txn["id"],
                predicted_category_id=shopping,
                predicted_confidence=0.9,
                status="PREDICTED",
            )
        )
        db.commit()

    r = client.delete(f"{URL}/{shopping}")
    assert r.status_code == 409
    assert r.json()["code"] == "CATEGORY_IN_USE"
