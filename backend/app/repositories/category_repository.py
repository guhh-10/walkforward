from sqlalchemy.orm import Session

from app.models import Category


def get_by_id(db: Session, category_id: int) -> Category | None:
    return db.get(Category, category_id)
