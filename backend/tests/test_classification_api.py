from pathlib import Path
from typing import Any

import httpx2
from fastapi.testclient import TestClient

from tests.conftest import CategoryIds

PREVIEW = "/api/classify/preview"
TXN = "/api/transactions"


def preview(client: TestClient, description: str, type: str = "expense") -> Any:
    r = client.post(PREVIEW, json={"description": description, "type": type})
    assert r.status_code == 200, r.text
    return r.json()


def create(client: TestClient, **body: Any) -> httpx2.Response:
    payload: dict[str, Any] = {
        "amount": 25,
        "type": "expense",
        "date": "2026-10-01",
        "description": "Gojek ride",
    }
    payload.update(body)
    return client.post(TXN, json=payload)


# ---------- no model: everything still works ----------
def test_preview_without_model_is_unavailable_not_an_error(client: TestClient) -> None:
    assert preview(client, "Gojek ride") == {
        "available": False,
        "predicted_category_id": None,
        "category_name": None,
        "confidence": None,
    }


def test_create_without_model_has_no_classification(
    client: TestClient, cat: CategoryIds
) -> None:
    r = create(client, category_id=cat["expense", "Transportation"])
    assert r.status_code == 201
    assert r.json()["classification"] is None


def test_create_without_model_or_category_is_rejected(client: TestClient) -> None:
    r = create(client)
    assert r.status_code == 422
    assert r.json()["code"] == "CATEGORY_REQUIRED"


# ---------- preview with a model ----------
def test_preview_predicts_a_category_with_confidence(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    body = preview(client, "Gojek ride to the office")
    assert body["available"] is True
    assert body["predicted_category_id"] == cat["expense", "Transportation"]
    assert body["category_name"] == "Transportation"
    assert 0.0 < body["confidence"] <= 1.0


def test_preview_only_offers_categories_of_the_requested_type(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    income_ids = {cat["income", "Salary"], cat["income", "Freelance"]}
    body = preview(client, "Gojek ride", type="income")
    assert body["predicted_category_id"] in income_ids

    expense_ids = {v for (t, _), v in cat.items() if t == "expense"}
    assert (
        preview(client, "monthly salary", type="expense")["predicted_category_id"]
        in expense_ids
    )


def test_preview_with_unusable_text_is_unavailable(
    client: TestClient, active_model: Path
) -> None:
    assert preview(client, "12345 67890")["available"] is False


def test_preview_validation(client: TestClient, active_model: Path) -> None:
    for body in (
        {"description": "   ", "type": "expense"},
        {"description": "x" * 501, "type": "expense"},
        {"description": "coffee", "type": "transfer"},
        {"type": "expense"},
    ):
        r = client.post(PREVIEW, json=body)
        assert r.status_code == 422
        assert r.json()["code"] == "VALIDATION_ERROR"


# ---------- create-time classification ----------
def test_create_without_category_uses_the_prediction(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    r = create(client, description="Alfamart snacks")
    assert r.status_code == 201
    body = r.json()
    assert body["category_id"] == cat["expense", "Groceries"]
    assert body["category_name"] == "Groceries"
    classification = body["classification"]
    assert classification["status"] == "PREDICTED"
    assert classification["predicted_category"] == "Groceries"
    assert classification["model_version"] == "v1"
    assert 0.0 < classification["confidence"] <= 1.0


def test_choosing_the_predicted_category_is_confirmed(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    r = create(client, category_id=cat["expense", "Transportation"])
    assert r.json()["classification"]["status"] == "CONFIRMED"


def test_choosing_a_different_category_is_a_manual_correction(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    r = create(client, category_id=cat["expense", "Dining/Coffee"])
    body = r.json()
    assert body["category_name"] == "Dining/Coffee"  # the final category is the user's
    assert body["classification"]["status"] == "MANUALLY_CORRECTED"
    assert body["classification"]["predicted_category"] == "Transportation"


def test_trivial_description_gets_no_prediction(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    r = create(client, description="12345", category_id=cat["expense", "Groceries"])
    assert r.status_code == 201
    assert r.json()["classification"] is None
    assert create(client, description="12345").status_code == 422


def test_classification_shows_in_lists_and_status_filter(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    create(client, description="Alfamart snacks")  # PREDICTED
    create(client, category_id=cat["expense", "Transportation"])  # CONFIRMED

    page = client.get(TXN).json()
    assert [t["classification"]["status"] for t in page["items"]] == [
        "CONFIRMED",
        "PREDICTED",
    ]
    queue = client.get(TXN, params={"status": "PREDICTED"}).json()
    assert queue["total"] == 1
    assert queue["items"][0]["description"] == "Alfamart snacks"


def test_classification_is_deleted_with_its_transaction(
    client: TestClient, active_model: Path
) -> None:
    txn = create(client, description="Alfamart snacks").json()
    assert client.delete(f"{TXN}/{txn['id']}").status_code == 204
    assert client.get(TXN, params={"status": "PREDICTED"}).json()["total"] == 0


# ---------- correction flow ----------
def put(client: TestClient, txn: dict[str, Any], **over: Any) -> httpx2.Response:
    """Send the transaction back the way the edit form does, with overrides applied."""
    body: dict[str, Any] = {
        "amount": txn["amount"],
        "type": txn["type"],
        "date": txn["date"],
        "description": txn["description"],
        "category_id": txn["category_id"],
    }
    body.update(over)
    return client.put(f"{TXN}/{txn['id']}", json=body)


def test_accepting_the_prediction_confirms_it(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    txn = create(client, description="Alfamart snacks").json()  # predicted Groceries
    r = put(client, txn)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category_id"] == cat["expense", "Groceries"]
    assert body["category_name"] == "Groceries"
    assert body["classification"]["status"] == "CONFIRMED"


def test_choosing_another_category_corrects_it(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    txn = create(client, description="Alfamart snacks").json()  # predicted Groceries
    body = put(client, txn, category_id=cat["expense", "Dining/Coffee"]).json()
    assert body["category_name"] == "Dining/Coffee"  # the final category is the user's
    assert body["classification"]["status"] == "MANUALLY_CORRECTED"
    assert body["classification"]["predicted_category"] == "Groceries"


def test_reviewed_transactions_leave_the_queue(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    first = create(client, description="Alfamart snacks").json()
    second = create(client, description="Gojek ride").json()
    assert client.get(TXN, params={"status": "PREDICTED"}).json()["total"] == 2

    put(client, first)  # accept
    put(client, second, category_id=cat["expense", "Shopping"])  # correct
    assert client.get(TXN, params={"status": "PREDICTED"}).json()["total"] == 0


def test_editing_the_description_repredicts_and_resets_status(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    txn = create(client, description="Gojek ride").json()  # predicted Transportation
    confirmed = put(client, txn).json()
    assert confirmed["classification"]["status"] == "CONFIRMED"

    body = put(client, confirmed, description="Alfamart snacks").json()
    assert body["classification"]["status"] == "PREDICTED"  # the old review is moot
    assert body["classification"]["predicted_category"] == "Groceries"
    assert body["classification"]["model_version"] == "v1"
    assert body["category_name"] == "Transportation"  # the user's category is kept


def test_update_without_a_usable_prediction_keeps_no_classification(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    txn = create(
        client, description="12345", category_id=cat["expense", "Groceries"]
    ).json()
    assert txn["classification"] is None
    r = put(client, txn, amount=7)
    assert r.status_code == 200
    assert r.json()["classification"] is None
    assert r.json()["amount"] == 7


# ---------- ML failures never block CRUD ----------
def test_missing_model_file_degrades_gracefully(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    active_model.unlink()
    assert preview(client, "Gojek ride")["available"] is False
    r = create(client, category_id=cat["expense", "Transportation"])
    assert r.status_code == 201
    assert r.json()["classification"] is None


def test_corrupt_model_file_degrades_gracefully(
    client: TestClient, cat: CategoryIds, active_model: Path
) -> None:
    active_model.write_bytes(b"this is not a pickle")
    assert preview(client, "Gojek ride")["available"] is False
    r = create(client, category_id=cat["expense", "Transportation"])
    assert r.status_code == 201
    assert client.get(f"{TXN}/{r.json()['id']}").status_code == 200
