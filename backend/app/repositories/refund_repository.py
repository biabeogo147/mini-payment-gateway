from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RefundStatus
from app.models.refund_transaction import RefundTransaction


def get_by_refund_transaction_id(
    db: Session,
    refund_transaction_id: str,
) -> RefundTransaction | None:
    return db.scalar(
        select(RefundTransaction).where(RefundTransaction.refund_transaction_id == refund_transaction_id)
    )


def get_by_merchant_refund_id(
    db: Session,
    merchant_db_id: UUID,
    refund_id: str,
) -> RefundTransaction | None:
    return db.scalar(
        select(RefundTransaction).where(
            RefundTransaction.merchant_db_id == merchant_db_id,
            RefundTransaction.refund_id == refund_id,
        )
    )


def get_by_payment_and_statuses(
    db: Session,
    payment_transaction_id: UUID,
    statuses: Iterable[RefundStatus],
) -> RefundTransaction | None:
    return db.scalar(
        select(RefundTransaction).where(
            RefundTransaction.payment_transaction_id == payment_transaction_id,
            RefundTransaction.status.in_(list(statuses)),
        )
    )


def create(
    db: Session,
    refund_transaction_id: str,
    merchant_db_id: UUID,
    payment_transaction_id: UUID,
    refund_id: str,
    refund_amount: Decimal,
    reason: str,
    idempotency_key: str | None = None,
) -> RefundTransaction:
    refund = RefundTransaction(
        refund_transaction_id=refund_transaction_id,
        merchant_db_id=merchant_db_id,
        payment_transaction_id=payment_transaction_id,
        refund_id=refund_id,
        refund_amount=refund_amount,
        reason=reason,
        status=RefundStatus.REFUND_PENDING,
        idempotency_key=idempotency_key,
    )
    db.add(refund)
    db.flush()
    return refund


def save(
    db: Session,
    refund: RefundTransaction,
) -> RefundTransaction:
    db.add(refund)
    db.flush()
    return refund
