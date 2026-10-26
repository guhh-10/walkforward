import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.repositories.transaction_repository import TransactionFilters
from app.schemas.classification import ClassificationStatus
from app.schemas.transaction import (
    TransactionIn,
    TransactionOut,
    TransactionPage,
    TransactionType,
)
from app.services import transaction_service

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(body: TransactionIn, db: DbSession) -> TransactionOut:
    txn = transaction_service.create_transaction(db, body)
    return TransactionOut.from_model(txn)


@router.get("", response_model=TransactionPage)
def list_transactions(
    db: DbSession,
    date_from: Annotated[dt.date | None, Query(alias="from")] = None,
    date_to: Annotated[dt.date | None, Query(alias="to")] = None,
    txn_type: Annotated[TransactionType | None, Query(alias="type")] = None,
    category_id: int | None = None,
    q: Annotated[str | None, Query(max_length=500)] = None,
    status_filter: Annotated[ClassificationStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> TransactionPage:
    filters = TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        type=txn_type,
        category_id=category_id,
        q=q,
        status=status_filter,
    )
    items, total = transaction_service.list_transactions(db, filters, page, page_size)
    return TransactionPage(
        items=[TransactionOut.from_model(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{txn_id}", response_model=TransactionOut)
def get_transaction(txn_id: int, db: DbSession) -> TransactionOut:
    return TransactionOut.from_model(transaction_service.get_transaction(db, txn_id))


@router.put("/{txn_id}", response_model=TransactionOut)
def update_transaction(
    txn_id: int, body: TransactionIn, db: DbSession
) -> TransactionOut:
    txn = transaction_service.update_transaction(db, txn_id, body)
    return TransactionOut.from_model(txn)


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(txn_id: int, db: DbSession) -> Response:
    transaction_service.delete_transaction(db, txn_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
