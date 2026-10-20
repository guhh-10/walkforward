import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.transaction import Transaction

TransactionType = Literal["income", "expense"]
ClassificationStatus = Literal["PREDICTED", "CONFIRMED", "MANUALLY_CORRECTED"]


class TransactionIn(BaseModel):
    """Request body for create and update (PUT replaces all fields)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: TransactionType
    date: dt.date
    description: str = Field(min_length=1, max_length=500)
    # Optional in the contract (ML fills it later); required until a model exists.
    category_id: int | None = None


class TransactionOut(BaseModel):
    id: int
    amount: float
    type: TransactionType
    date: dt.date
    description: str
    category_id: int
    category_name: str
    is_future: bool
    classification: None = None  # populated in the classification stage
    created_at: dt.datetime
    updated_at: dt.datetime

    @classmethod
    def from_model(cls, txn: "Transaction") -> "TransactionOut":
        return cls(
            id=txn.id,
            amount=txn.amount_cents / 100,
            type=cast(TransactionType, txn.type),
            date=txn.txn_date,
            description=txn.description,
            category_id=txn.category_id,
            category_name=txn.category.name,
            is_future=txn.txn_date > dt.date.today(),
            created_at=txn.created_at,
            updated_at=txn.updated_at,
        )


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
