from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Classification, Transaction
from app.repositories import (
    category_repository,
    classification_repository,
    transaction_repository,
)
from app.repositories.transaction_repository import TransactionFilters
from app.schemas.transaction import TransactionIn
from app.services import classifier_service
from app.services.errors import NotFoundError, ValidationDomainError


def to_cents(amount: Decimal) -> int:
    """Convert major units (already validated to <= 2 decimals) to integer cents."""
    return int((amount * 100).quantize(Decimal(1)))


def _validate_category(db: Session, category_id: int | None, txn_type: str) -> int:
    if category_id is None:
        raise ValidationDomainError("CATEGORY_REQUIRED", "category_id is required.")
    category = category_repository.get_by_id(db, category_id)
    if category is None:
        raise ValidationDomainError(
            "CATEGORY_NOT_FOUND", f"Category {category_id} does not exist."
        )
    if category.type != txn_type:
        raise ValidationDomainError(
            "CATEGORY_TYPE_MISMATCH",
            f"Category '{category.name}' is {category.type}, "
            f"but the transaction is {txn_type}.",
        )
    return category.id


def get_transaction(db: Session, txn_id: int) -> Transaction:
    txn = transaction_repository.get(db, txn_id)
    if txn is None:
        raise NotFoundError("TRANSACTION_NOT_FOUND", f"Transaction {txn_id} not found.")
    return txn


def create_transaction(db: Session, data: TransactionIn) -> Transaction:
    # The classifier is optional: with no model (or no usable prediction) the
    # transaction is still created, provided the caller chose a category.
    prediction = classifier_service.predict(db, data.description, data.type)

    if data.category_id is None:
        if prediction is None:
            raise ValidationDomainError(
                "CATEGORY_REQUIRED",
                "category_id is required: no classifier prediction is available.",
            )
        category_id, status = prediction.category_id, "PREDICTED"
    else:
        category_id = _validate_category(db, data.category_id, data.type)
        accepted = prediction is not None and prediction.category_id == category_id
        status = "CONFIRMED" if accepted else "MANUALLY_CORRECTED"

    txn = Transaction(
        amount_cents=to_cents(data.amount),
        type=data.type,
        txn_date=data.date,
        description=data.description,
        category_id=category_id,
    )
    transaction_repository.add(db, txn)
    if prediction is not None:
        classification_repository.add(
            db,
            Classification(
                transaction_id=txn.id,
                model_version_id=prediction.model_version_id,
                predicted_category_id=prediction.category_id,
                predicted_confidence=prediction.confidence,
                status=status,
            ),
        )
    db.commit()
    db.expire(txn)  # reload server defaults and the classification relationship
    return get_transaction(db, txn.id)


def _review_transition(txn: Transaction, category_id: int) -> None:
    """Accepting the prediction confirms it; a different category is a correction."""
    classification = txn.classification
    if classification is None:
        return
    classification.status = (
        "CONFIRMED"
        if category_id == classification.predicted_category_id
        else "MANUALLY_CORRECTED"
    )


def _reclassify(db: Session, txn: Transaction) -> None:
    """A changed description makes the old guess moot: predict again, in place."""
    prediction = classifier_service.predict(db, txn.description, txn.type)
    if prediction is None:
        return
    classification = txn.classification
    if classification is None:
        classification_repository.add(
            db,
            Classification(
                transaction_id=txn.id,
                model_version_id=prediction.model_version_id,
                predicted_category_id=prediction.category_id,
                predicted_confidence=prediction.confidence,
                status="PREDICTED",
            ),
        )
        return
    classification.model_version_id = prediction.model_version_id
    classification.predicted_category_id = prediction.category_id
    classification.predicted_confidence = prediction.confidence
    classification.status = "PREDICTED"


def update_transaction(db: Session, txn_id: int, data: TransactionIn) -> Transaction:
    txn = get_transaction(db, txn_id)
    category_id = _validate_category(db, data.category_id, data.type)
    description_changed = data.description != txn.description

    txn.amount_cents = to_cents(data.amount)
    txn.type = data.type
    txn.txn_date = data.date
    txn.description = data.description
    txn.category_id = category_id

    # §3.3: an edited description invalidates the review outcome and is re-predicted;
    # otherwise the user's chosen category confirms or corrects the prediction.
    if description_changed:
        _reclassify(db, txn)
    else:
        _review_transition(txn, category_id)

    db.commit()
    db.expire(txn)  # refresh updated_at, the category, and the classification
    return get_transaction(db, txn_id)


def delete_transaction(db: Session, txn_id: int) -> None:
    txn = get_transaction(db, txn_id)
    transaction_repository.delete(db, txn)
    db.commit()


def list_transactions(
    db: Session, filters: TransactionFilters, page: int, page_size: int
) -> tuple[list[Transaction], int]:
    return transaction_repository.list_page(db, filters, page, page_size)
