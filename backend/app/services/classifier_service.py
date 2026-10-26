"""Inference glue between the database and the ML layer.

Any ML problem (no model, missing or corrupt artifact, prediction error) is
logged and reported as "no prediction", so transaction CRUD is never blocked.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.ml import classifier
from app.ml.classifier import TextClassifier
from app.repositories import category_repository, model_repository
from app.schemas.classification import ClassifyPreviewOut

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CategoryPrediction:
    category_id: int
    category_name: str
    confidence: float
    model_version_id: int


@lru_cache(maxsize=2)
def _load(path: str, mtime_ns: int) -> TextClassifier:
    # mtime_ns is part of the cache key so a retrained artifact is reloaded.
    return classifier.load_pipeline(Path(path))


def _artifact_path(stored: str) -> Path:
    path = Path(stored)
    return path if path.is_absolute() else BACKEND_DIR / path


def predict(db: Session, description: str, txn_type: str) -> CategoryPrediction | None:
    """Best category of the right type for `description`, or None."""
    version = model_repository.get_active(db)
    if version is None:
        return None

    categories = category_repository.list_all(db, txn_type)
    names = {c.id: c.name for c in categories}
    try:
        path = _artifact_path(version.artifact_path)
        model = _load(str(path), path.stat().st_mtime_ns)
        result = classifier.predict(model, description, allowed=names.keys())
    except Exception:
        logger.warning("Classifier unavailable; continuing without it.", exc_info=True)
        return None

    if result is None:
        return None
    return CategoryPrediction(
        category_id=result.label,
        category_name=names[result.label],
        confidence=result.confidence,
        model_version_id=version.id,
    )


def preview(db: Session, description: str, txn_type: str) -> ClassifyPreviewOut:
    prediction = predict(db, description, txn_type)
    if prediction is None:
        return ClassifyPreviewOut(available=False)
    return ClassifyPreviewOut(
        available=True,
        predicted_category_id=prediction.category_id,
        category_name=prediction.category_name,
        confidence=prediction.confidence,
    )
