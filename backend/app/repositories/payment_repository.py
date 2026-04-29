from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus
from app.models.payment_transaction import PaymentTransaction


def get_by_transaction_id(
    db: Session,
    transaction_id: str,
) -> PaymentTransaction | None:
    return db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.transaction_id == transaction_id)
    )


def get_latest_by_merchant_order(
    db: Session,
    merchant_db_id: UUID,
    order_id: str,
) -> PaymentTransaction | None:
    return db.scalar(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.merchant_db_id == merchant_db_id,
            PaymentTransaction.order_id == order_id,
        )
        .order_by(PaymentTransaction.created_at.desc(), PaymentTransaction.transaction_id.desc())
        .limit(1)
    )


def get_pending_by_merchant_order(
    db: Session,
    merchant_db_id: UUID,
    order_id: str,
) -> PaymentTransaction | None:
    return db.scalar(
        select(PaymentTransaction).where(
            PaymentTransaction.merchant_db_id == merchant_db_id,
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.status == PaymentStatus.PENDING,
        )
    )


def create(
    db: Session,
    transaction_id: str,
    merchant_db_id: UUID,
    order_reference_id: UUID,
    order_id: str,
    amount: Decimal,
    currency: str,
    description: str,
    qr_content: str,
    expire_at: datetime,
    idempotency_key: str | None = None,
) -> PaymentTransaction:
    payment = PaymentTransaction(
        transaction_id=transaction_id,
        merchant_db_id=merchant_db_id,
        order_reference_id=order_reference_id,
        order_id=order_id,
        amount=amount,
        currency=currency,
        description=description,
        status=PaymentStatus.PENDING,
        qr_content=qr_content,
        expire_at=expire_at,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    db.flush()
    return payment
