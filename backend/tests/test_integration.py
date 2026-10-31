"""Integration test: one path from raw records to a reviewed forecast.

Unlike the other suites, this one does not isolate a single layer. It drives the
whole application the way a person would — enter a year of history, train the
classifier from the CLI, let it label a new transaction, forecast from the
history, then correct that label — and checks the pieces agree with each other.
"""

import datetime as dt
from pathlib import Path

from app.ml.months import month_of, next_month
from app.models import ModelVersion
from app.scripts import train_classifier
from app.services import training_service
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import TRAINING_DATA, CategoryIds

TXN = "/api/transactions"
FORECAST = "/api/forecasts"

EXPENSE_CLASSES = ("Groceries", "Transportation", "Dining/Coffee")
INCOME_CLASSES = ("Salary", "Freelance")


def month_start(months_ago: int) -> dt.date:
    today = dt.date.today()
    index = today.year * 12 + (today.month - 1) - months_ago
    return dt.date(index // 12, index % 12 + 1, 1)


def seed_a_year(client: TestClient, cat: CategoryIds) -> None:
    """Twelve complete months of labelled income and expense, all through the API."""
    for months_ago in range(12, 0, -1):
        date = month_start(months_ago).isoformat()
        for offset, name in enumerate(EXPENSE_CLASSES):
            examples = TRAINING_DATA["expense", name]
            r = client.post(
                TXN,
                json={
                    "amount": 100 + offset,
                    "type": "expense",
                    "date": date,
                    "description": examples[months_ago % len(examples)],
                    "category_id": cat["expense", name],
                },
            )
            assert r.status_code == 201, r.text
        name = INCOME_CLASSES[months_ago % len(INCOME_CLASSES)]
        examples = TRAINING_DATA["income", name]
        r = client.post(
            TXN,
            json={
                "amount": 5000,
                "type": "income",
                "date": date,
                "description": examples[months_ago % len(examples)],
                "category_id": cat["income", name],
            },
        )
        assert r.status_code == 201, r.text


def version_rows(session_factory: sessionmaker[Session]) -> list[tuple[int, str, bool]]:
    with session_factory() as db:
        return [
            (v.id, v.version_tag, v.is_active)
            for v in db.scalars(select(ModelVersion).order_by(ModelVersion.id))
        ]


def run_training_cli(
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Invoke the real training CLI, aiming its artifact at tmp_path."""
    monkeypatch.setattr(train_classifier, "SessionLocal", session_factory)
    original = training_service.train_new_version

    def train_into_tmp(db: Session, algorithm: str, test_size: float) -> ModelVersion:
        return original(db, algorithm, test_size, tmp_path)

    monkeypatch.setattr(training_service, "train_new_version", train_into_tmp)
    assert train_classifier.main([]) == 0


def test_records_to_a_reviewed_forecast(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch,
) -> None:
    # 1. A year of history, entered by the user. It is also the first training set.
    seed_a_year(client, cat)

    # 2. Train explicitly, once, from the CLI — never automatically.
    run_training_cli(session_factory, tmp_path, monkeypatch)
    rows = version_rows(session_factory)
    assert [(tag, active) for _, tag, active in rows] == [("v1", True)]

    # 3. A new transaction with no category gets a prediction straight away.
    created = client.post(
        TXN,
        json={
            "amount": 42,
            "type": "expense",
            "date": month_start(0).isoformat(),
            "description": "Gojek ride to the office",
        },
    )
    assert created.status_code == 201, created.text
    txn = created.json()
    assert txn["classification"] is not None
    assert txn["classification"]["status"] == "PREDICTED"
    assert txn["classification"]["predicted_category"] == "Transportation"
    assert txn["classification"]["model_version"] == "v1"
    assert 0.0 <= txn["classification"]["confidence"] <= 1.0
    assert txn["category_id"] == txn["classification"]["predicted_category_id"]

    # 4. Forecast from the same history: shape, ordering, reliability.
    forecast = client.post(FORECAST)
    assert forecast.status_code == 200, forecast.text
    body = forecast.json()
    assert 0 <= body["optimistic"] <= body["baseline"] <= body["conservative"]
    assert body["selected_model"] in body["backtest"]["per_model"]
    assert set(body["backtest"]["per_model"]) == {"naive", "ma3", "ses"}
    assert body["target_month"] == next_month(month_of(dt.date.today()))
    assert body["history_months"] == 12
    assert body["reliability"] == "medium"

    # 5. Correct the prediction. The user's choice wins; the guess is kept as a record.
    versions_before = version_rows(session_factory)
    artifacts_before = sorted(p.name for p in tmp_path.iterdir())

    corrected = client.put(
        f"{TXN}/{txn['id']}",
        json={
            "amount": txn["amount"],
            "type": txn["type"],
            "date": txn["date"],
            "description": txn["description"],
            "category_id": cat["expense", "Dining/Coffee"],
        },
    )
    assert corrected.status_code == 200, corrected.text
    after = corrected.json()
    assert after["category_id"] == cat["expense", "Dining/Coffee"]
    assert after["classification"]["status"] == "MANUALLY_CORRECTED"
    guessed = after["classification"]["predicted_category"]
    assert guessed == "Transportation"  # the original guess is kept for the record

    # A correction is data, not training: no new version, no new artifact.
    assert version_rows(session_factory) == versions_before
    assert sorted(p.name for p in tmp_path.iterdir()) == artifacts_before

    # And the transaction has left the review queue.
    queue = client.get(TXN, params={"status": "PREDICTED"}).json()
    assert txn["id"] not in {item["id"] for item in queue["items"]}
