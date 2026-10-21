from pydantic import BaseModel

from app.schemas.category import CategoryType


class CategoryBreakdown(BaseModel):
    category_id: int
    name: str
    type: CategoryType
    total: float
    pct: float  # share of the total for this category's type, 0-100


class MonthlySummary(BaseModel):
    month: str  # YYYY-MM
    income: float
    expense: float
    net: float
    by_category: list[CategoryBreakdown]


class TrendPoint(BaseModel):
    month: str  # YYYY-MM
    income: float
    expense: float
    net: float
