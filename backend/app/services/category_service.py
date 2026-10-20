from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Category
from app.repositories import category_repository
from app.schemas.category import CategoryIn
from app.services.errors import ConflictError, NotFoundError


def list_categories(db: Session, category_type: str | None = None) -> list[Category]:
    return category_repository.list_all(db, category_type)


def create_category(db: Session, data: CategoryIn) -> Category:
    duplicate = ConflictError(
        "CATEGORY_EXISTS",
        f"A {data.type} category named '{data.name}' already exists.",
    )
    if category_repository.find_by_name_and_type(db, data.name, data.type):
        raise duplicate
    category = Category(name=data.name, type=data.type, is_default=False)
    try:
        category_repository.add(db, category)
        db.commit()
    except IntegrityError:  # lost a race against the UNIQUE(name, type) constraint
        db.rollback()
        raise duplicate from None
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = category_repository.get_by_id(db, category_id)
    if category is None:
        raise NotFoundError("CATEGORY_NOT_FOUND", f"Category {category_id} not found.")

    n_txns = category_repository.count_transactions(db, category_id)
    n_preds = category_repository.count_classification_refs(db, category_id)
    if n_txns or n_preds:
        raise ConflictError(
            "CATEGORY_IN_USE",
            f"Category '{category.name}' is used by {n_txns} transaction(s) and "
            f"{n_preds} stored prediction(s). Reassign them before deleting.",
        )
    category_repository.delete(db, category)
    db.commit()
