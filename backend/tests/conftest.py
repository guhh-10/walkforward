from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.database.connection import Base
from app.database.dependencies import get_db
from app.database.seed import seed_categories
from app.main import app
from app.ml import classifier
from app.models import Category, ModelVersion
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry, StaticPool

CategoryIds = dict[tuple[str, str], int]


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(  # pyright: ignore[reportUnusedFunction]
        dbapi_connection: DBAPIConnection, connection_record: ConnectionPoolEntry
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        seed_categories(db)
    yield factory
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def _override() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def cat(session_factory: sessionmaker[Session]) -> CategoryIds:
    """Lookup of seeded category ids: cat['expense', 'Groceries']."""
    with session_factory() as db:
        rows = db.scalars(select(Category)).all()
        return {(c.type, c.name): c.id for c in rows}


# ---------- trained classifier ----------
TRAINING_DATA: dict[tuple[str, str], list[str]] = {
    ("expense", "Groceries"): [
        "Indomaret groceries",
        "Alfamart snacks",
        "supermarket vegetables",
        "belanja bulanan Indomaret",
        "Alfamart milk and bread",
        "groceries at the market",
    ],
    ("expense", "Transportation"): [
        "Gojek ride",
        "Grab car to office",
        "taxi airport",
        "Gojek ride home",
        "bus ticket",
        "Grab bike",
    ],
    ("expense", "Dining/Coffee"): [
        "Kopi Kenangan coffee",
        "warung makan lunch",
        "restaurant dinner",
        "coffee shop latte",
        "warung nasi lunch",
        "dinner at restaurant",
    ],
    ("income", "Salary"): [
        "monthly salary",
        "gaji bulanan",
        "payroll deposit",
        "salary payment",
        "gaji november",
        "payroll salary",
    ],
    ("income", "Freelance"): [
        "freelance project payment",
        "client invoice paid",
        "freelance logo design",
        "invoice from client",
        "freelance website job",
        "client project fee",
    ],
}


@pytest.fixture
def active_model(
    session_factory: sessionmaker[Session], cat: CategoryIds, tmp_path: Path
) -> Path:
    """Train a tiny classifier, save it, and register it as the active model."""
    texts: list[str] = []
    labels: list[int] = []
    for key, examples in TRAINING_DATA.items():
        texts.extend(examples)
        labels.extend([cat[key]] * len(examples))

    path = tmp_path / "category_clf_v1.joblib"
    classifier.save_pipeline(
        classifier.fit_pipeline(texts, labels, "logreg_tfidf"), path
    )
    with session_factory() as db:
        db.add(
            ModelVersion(
                version_tag="v1",
                algorithm="logreg_tfidf",
                trained_at=datetime.now(UTC).replace(tzinfo=None),
                dataset_size=len(texts),
                train_metrics_json="{}",
                artifact_path=str(path),
                is_active=True,
            )
        )
        db.commit()
    return path
