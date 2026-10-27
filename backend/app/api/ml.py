from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.evaluation import EvaluationOut
from app.services import evaluation_service

router = APIRouter(prefix="/api/ml", tags=["ml"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/evaluation/latest", response_model=EvaluationOut)
def latest_evaluation(db: DbSession) -> EvaluationOut:
    """The active classifier's evaluation report (404 NO_ACTIVE_MODEL if none)."""
    return evaluation_service.latest_evaluation(db)
