from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.category import CategoryIn, CategoryOut, CategoryType
from app.services import category_service

router = APIRouter(prefix="/api/categories", tags=["categories"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: DbSession,
    category_type: Annotated[CategoryType | None, Query(alias="type")] = None,
) -> list[CategoryOut]:
    categories = category_service.list_categories(db, category_type)
    return [CategoryOut.from_model(c) for c in categories]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryIn, db: DbSession) -> CategoryOut:
    return CategoryOut.from_model(category_service.create_category(db, body))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession) -> Response:
    category_service.delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
