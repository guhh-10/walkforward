from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Transaction
from app.repositories import category_repository, transaction_repository
from app.repositories.transaction_repository import TransactionFilters
from app.schemas.transaction import TransactionIn
from app.services.errors import NotFoundError, ValidationDomainError


def to_cents(amount: Decimal) -> int:
    """Convert major units (already validated to <= 2 decimals) to integer cents."""
    return int((amount * 100).quantize(Decimal(1)))


def _resolve_category_id(db: Session, data: TransactionIn) -> int:
    # Until the classifier exists (stage 8) the final category must be supplied.
    if data.category_id is None:
        raise ValidationDomainError(
            "CATEGORY_REQUIRED",
            "category_id is required when no classifier is available.",
        )
    category = category_repository.get_by_id(db, data.category_id)
    if category is None:
        raise ValidationDomainError(
            "CATEGORY_NOT_FOUND", f"Category {data.category_id} does not exist."
        )
    if category.type != data.type:
        raise ValidationDomainError(
            "CATEGORY_TYPE_MISMATCH",
            f"Category '{category.name}' is {category.type}, "
            f"but the transaction is {data.type}.",
        )
    return category.id


def get_transaction(db: Session, txn_id: int) -> Transaction:
    txn = transaction_repository.get(db, txn_id)
    if txn is None:
        raise NotFoundError("TRANSACTION_NOT_FOUND", f"Transaction {txn_id} not found.")
    return txn


def create_transaction(db: Session, data: TransactionIn) -> Transaction:
    category_id = _resolve_category_id(db, data)
    txn = Transaction(
        amount_cents=to_cents(data.amount),
        type=data.type,
        txn_date=data.date,
        description=data.description,
        category_id=category_id,
    )
    transaction_repository.add(db, txn)
    db.commit()
    return get_transaction(db, txn.id)


def update_transaction(db: Session, txn_id: int, data: TransactionIn) -> Transaction:
    txn = get_transaction(db, txn_id)
    category_id = _resolve_category_id(db, data)
    txn.amount_cents = to_cents(data.amount)
    txn.type = data.type
    txn.txn_date = data.date
    txn.description = data.description
    txn.category_id = category_id
    # Classification status transitions (CONFIRMED / MANUALLY_CORRECTED)
    # will hook in here in the classification stage.
    db.commit()
    db.expire(txn)  # refresh server-side updated_at and the category relationship
    return get_transaction(db, txn_id)


def delete_transaction(db: Session, txn_id: int) -> None:
    txn = get_transaction(db, txn_id)
    transaction_repository.delete(db, txn)
    db.commit()


def list_transactions(
    db: Session, filters: TransactionFilters, page: int, page_size: int
) -> tuple[list[Transaction], int]:
    return transaction_repository.list_page(db, filters, page, page_size)
