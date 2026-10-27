from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.repositories import model_repository
from app.schemas.evaluation import EvaluationOut, MetricsOut
from app.services.errors import DomainError, NotFoundError


def latest_evaluation(db: Session) -> EvaluationOut:
    version = model_repository.get_active(db)
    if version is None:
        raise NotFoundError(
            "NO_ACTIVE_MODEL",
            "No classifier has been trained yet. "
            "Run: python -m app.scripts.train_classifier",
        )
    try:
        metrics = MetricsOut.model_validate_json(version.train_metrics_json)
    except ValidationError:
        raise DomainError(
            500, "METRICS_UNREADABLE", "The stored evaluation report is unreadable."
        ) from None
    return EvaluationOut(
        version_tag=version.version_tag,
        algorithm=version.algorithm,
        trained_at=version.trained_at,
        dataset_size=version.dataset_size,
        metrics=metrics,
    )
