import json
from pathlib import Path
from typing import Any

import pytest
from app.ml.classifier import InsufficientDataError
from app.models import Classification, ModelVersion
from app.scripts import train_classifier
from app.services import training_service
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tests.conftest import TRAINING_DATA, CategoryIds

TXN = "/api/transactions"
EVALUATION = "/api/ml/evaluation/latest"


def seed_reviewed(client: TestClient, cat: CategoryIds) -> int:
    """Create one transaction per training example, categories chosen by the user."""
    count = 0
    for (kind, name), examples in TRAINING_DATA.items():
        for i, description in enumerate(examples):
            r = client.post(
                TXN,
                json={
                    "amount": 10 + i,
                    "type": kind,
                    "date": f"2026-0{1 + i}-15",
                    "description": description,
                    "category_id": cat[kind, name],
                },
            )
            assert r.status_code == 201, r.text
            count += 1
    return count


def versions(session_factory: sessionmaker[Session]) -> list[ModelVersion]:
    with session_factory() as db:
        return list(db.scalars(select(ModelVersion).order_by(ModelVersion.id)))


# ---------- service ----------
def test_training_script_creates_new_version_and_activates(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    total = seed_reviewed(client, cat)
    with session_factory() as db:
        version = training_service.train_new_version(
            db, "logreg_tfidf", artifact_dir=tmp_path
        )
        assert (version.version_tag, version.is_active) == ("v1", True)
        assert version.dataset_size == total
        assert Path(version.artifact_path).exists()

    with session_factory() as db:
        second = training_service.train_new_version(
            db, "complement_nb", artifact_dir=tmp_path
        )
        assert second.version_tag == "v2"

    v1, v2 = versions(session_factory)
    assert (v1.is_active, v2.is_active) == (False, True)  # only one active version
    assert v2.algorithm == "complement_nb"


def test_metrics_are_persisted_with_the_version(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    seed_reviewed(client, cat)
    with session_factory() as db:
        version = training_service.train_new_version(
            db, "logreg_tfidf", artifact_dir=tmp_path
        )
        metrics: dict[str, Any] = json.loads(version.train_metrics_json)
    assert metrics["seed"] == 42
    assert metrics["n_train"] + metrics["n_test"] == version.dataset_size
    assert len(metrics["per_class"]) == 5
    assert sum(c["support"] for c in metrics["per_class"]) == metrics["n_test"]


def test_training_is_reproducible(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    seed_reviewed(client, cat)
    with session_factory() as db:
        a = training_service.train_new_version(
            db, "logreg_tfidf", artifact_dir=tmp_path
        )
        b = training_service.train_new_version(
            db, "logreg_tfidf", artifact_dir=tmp_path
        )
        assert a.train_metrics_json == b.train_metrics_json


def test_unreviewed_predictions_are_not_training_data(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    seed_reviewed(client, cat)
    # Two more transactions whose category is only a model guess (PREDICTED).
    guessed: list[int] = []
    for description in ("mystery shop alpha", "mystery shop beta"):
        r = client.post(
            TXN,
            json={
                "amount": 5,
                "type": "expense",
                "date": "2026-09-01",
                "description": description,
                "category_id": cat["expense", "Groceries"],
            },
        )
        guessed.append(r.json()["id"])
    with session_factory() as db:
        for txn_id in guessed:
            db.add(
                Classification(
                    transaction_id=txn_id,
                    predicted_category_id=cat["expense", "Groceries"],
                    predicted_confidence=0.5,
                    status="PREDICTED",
                )
            )
        db.commit()
        version = training_service.train_new_version(
            db, "logreg_tfidf", artifact_dir=tmp_path
        )
    assert version.dataset_size == 30  # the two PREDICTED rows are left out


def test_too_little_data_raises_and_creates_nothing(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    client.post(
        TXN,
        json={
            "amount": 1,
            "type": "expense",
            "date": "2026-01-01",
            "description": "only one",
            "category_id": cat["expense", "Groceries"],
        },
    )
    with session_factory() as db, pytest.raises(InsufficientDataError):
        training_service.train_new_version(db, "logreg_tfidf", artifact_dir=tmp_path)
    assert versions(session_factory) == []
    assert list(tmp_path.iterdir()) == []


def test_trained_model_is_used_for_predictions_straight_away(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    seed_reviewed(client, cat)
    with session_factory() as db:
        training_service.train_new_version(db, "logreg_tfidf", artifact_dir=tmp_path)
    body = client.post(
        "/api/classify/preview", json={"description": "Gojek ride", "type": "expense"}
    ).json()
    assert body["available"] is True
    assert body["predicted_category_id"] == cat["expense", "Transportation"]


# ---------- CLI ----------
def test_cli_trains_and_reports(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    seed_reviewed(client, cat)
    monkeypatch.setattr(train_classifier, "SessionLocal", session_factory)
    original = training_service.train_new_version

    def train_into_tmp(db: Session, algorithm: str, test_size: float) -> ModelVersion:
        return original(db, algorithm, test_size, tmp_path)

    monkeypatch.setattr(training_service, "train_new_version", train_into_tmp)

    code = train_classifier.main(
        ["--algorithm", "complement_nb", "--test-size", "0.25"]
    )
    assert code == 0
    assert "Trained v1 (complement_nb)" in capsys.readouterr().out
    assert versions(session_factory)[0].algorithm == "complement_nb"


def test_cli_exits_with_a_message_when_data_is_insufficient(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(train_classifier, "SessionLocal", session_factory)
    assert train_classifier.main([]) == 1
    assert "Training aborted" in capsys.readouterr().err


def test_cli_rejects_bad_arguments() -> None:
    with pytest.raises(SystemExit):
        train_classifier.parse_args(["--algorithm", "svm"])
    with pytest.raises(SystemExit):
        train_classifier.parse_args(["--test-size", "1.5"])


# ---------- evaluation endpoint ----------
def test_evaluation_without_a_model_is_404(client: TestClient) -> None:
    r = client.get(EVALUATION)
    assert r.status_code == 404
    assert r.json()["code"] == "NO_ACTIVE_MODEL"


def test_evaluation_endpoint_returns_the_active_report(
    client: TestClient,
    cat: CategoryIds,
    session_factory: sessionmaker[Session],
    tmp_path: Path,
) -> None:
    seed_reviewed(client, cat)
    with session_factory() as db:
        training_service.train_new_version(db, "logreg_tfidf", artifact_dir=tmp_path)
        training_service.train_new_version(db, "complement_nb", artifact_dir=tmp_path)

    body = client.get(EVALUATION).json()
    assert (body["version_tag"], body["algorithm"]) == ("v2", "complement_nb")
    assert body["dataset_size"] == 30
    metrics = body["metrics"]
    for key in ("accuracy", "macro_f1", "weighted_f1"):
        assert 0.0 <= metrics[key] <= 1.0
    assert len(metrics["per_class"]) == 5
    labels = metrics["confusion_matrix"]["labels"]
    matrix = metrics["confusion_matrix"]["matrix"]
    assert len(labels) == len(matrix) == 5
    assert all(len(row) == 5 for row in matrix)
    assert sum(map(sum, matrix)) == metrics["n_test"]


def test_unreadable_stored_metrics_give_a_clear_error(
    client: TestClient, active_model: Path
) -> None:
    r = client.get(EVALUATION)  # the fixture stores "{}" as its metrics
    assert r.status_code == 500
    assert r.json()["code"] == "METRICS_UNREADABLE"
