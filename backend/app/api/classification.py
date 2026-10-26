from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.classification import ClassifyPreviewIn, ClassifyPreviewOut
from app.services import classifier_service

router = APIRouter(prefix="/api/classify", tags=["classification"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/preview", response_model=ClassifyPreviewOut)
def preview(body: ClassifyPreviewIn, db: DbSession) -> ClassifyPreviewOut:
    """Predict a category without saving anything; `available: false` if no model."""
    return classifier_service.preview(db, body.description, body.type)
