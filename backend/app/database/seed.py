from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category

DEFAULT_CATEGORIES = {
    "income": [
        "Salary",
        "Freelance",
        "Investment",
        "Other",
    ],
    "expense": [
        "Housing",
        "Utilities",
        "Groceries",
        "Dining/Coffee",
        "Transportation",
        "Healthcare",
        "Education",
        "Entertainment",
        "Shopping",
        "Subscriptions",
        "Other",
    ],
}


def seed_categories(db: Session) -> None:
    """Insert missing default categories without duplicating existing ones."""

    for category_type, names in DEFAULT_CATEGORIES.items():
        for name in names:
            existing = db.scalar(
                select(Category).where(
                    Category.name == name,
                    Category.type == category_type,
                )
            )

            if existing is None:
                db.add(
                    Category(
                        name=name,
                        type=category_type,
                        is_default=True,
                    )
                )

    db.commit()