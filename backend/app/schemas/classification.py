from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryType

if TYPE_CHECKING:
    from app.models.classification import Classification

ClassificationStatus = Literal["PREDICTED", "CONFIRMED", "MANUALLY_CORRECTED"]


class ClassificationOut(BaseModel):
    predicted_category_id: int
    predicted_category: str
    confidence: float
    status: ClassificationStatus
    model_version: str | None

    @classmethod
    def from_model(cls, c: "Classification") -> "ClassificationOut":
        return cls(
            predicted_category_id=c.predicted_category_id,
            predicted_category=c.predicted_category.name,
            confidence=c.predicted_confidence,
            status=cast(ClassificationStatus, c.status),
            model_version=c.model_version.version_tag if c.model_version else None,
        )


class ClassifyPreviewIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=500)
    type: CategoryType


class ClassifyPreviewOut(BaseModel):
    """`available` is false when there is no usable model or prediction."""

    available: bool
    predicted_category_id: int | None = None
    category_name: str | None = None
    confidence: float | None = None
