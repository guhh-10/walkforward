"""Train, evaluate, persist and activate a new classifier version."""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.ml import classifier
from app.ml.preprocessing import LabeledRow, build_labeled_dataset
from app.models import ModelVersion
from app.repositories import (
    category_repository,
    classification_repository,
    model_repository,
)
from app.services.classifier_service import BACKEND_DIR

DEFAULT_ARTIFACT_DIR = BACKEND_DIR / "models_artifacts"


def _display_names(db: Session) -> tuple[dict[int, str], dict[int, str]]:
    """Category names (suffixed with the type when a name exists in both) and types."""
    categories = category_repository.list_all(db)
    counts = Counter(c.name for c in categories)
    names = {
        c.id: f"{c.name} ({c.type})" if counts[c.name] > 1 else c.name
        for c in categories
    }
    return names, {c.id: c.type for c in categories}


def _stored_path(path: Path) -> str:
    """Relative to the backend folder when possible, so the repo can move."""
    try:
        return path.resolve().relative_to(BACKEND_DIR).as_posix()
    except ValueError:
        return str(path)


def train_new_version(
    db: Session,
    algorithm: str,
    test_size: float = classifier.DEFAULT_TEST_SIZE,
    artifact_dir: Path = DEFAULT_ARTIFACT_DIR,
) -> ModelVersion:
    """Train on reviewed transactions and make the result the active model.

    Raises classifier.InsufficientDataError when there is too little data.
    """
    rows = classification_repository.reviewed_training_rows(db)
    dataset = build_labeled_dataset(
        LabeledRow(text=r.description, label=r.category_id, group=r.type) for r in rows
    )
    names, groups = _display_names(db)
    trained = classifier.train_and_evaluate(
        dataset, algorithm, names, groups, test_size=test_size
    )

    tag = model_repository.next_version_tag(db)
    path = artifact_dir / f"category_clf_{tag}.joblib"
    classifier.save_pipeline(trained.model, path)

    model_repository.deactivate_all(db)
    version = model_repository.add(
        db,
        ModelVersion(
            version_tag=tag,
            algorithm=algorithm,
            trained_at=datetime.now(UTC).replace(tzinfo=None),
            dataset_size=len(dataset),
            train_metrics_json=json.dumps(trained.report.to_dict()),
            artifact_path=_stored_path(path),
            is_active=True,
        ),
    )
    db.commit()
    return version
