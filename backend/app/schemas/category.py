import datetime as dt
from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.category import Category

CategoryType = Literal["income", "expense"]


class CategoryIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    type: CategoryType


class CategoryOut(BaseModel):
    id: int
    name: str
    type: CategoryType
    is_default: bool
    created_at: dt.datetime

    @classmethod
    def from_model(cls, category: "Category") -> "CategoryOut":
        return cls(
            id=category.id,
            name=category.name,
            type=cast(CategoryType, category.type),
            is_default=category.is_default,
            created_at=category.created_at,
        )
