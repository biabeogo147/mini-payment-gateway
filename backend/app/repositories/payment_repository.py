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


def get_by_id(
    db: Session,
    payment_transaction_id: UUID,
) -> PaymentTransaction | None:
    return db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.id == payment_transaction_id)
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


def get_success_by_merchant_order(
    db: Session,
    merchant_db_id: UUID,
    order_id: str,
) -> PaymentTransaction | None:
    return db.scalar(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.merchant_db_id == merchant_db_id,
            PaymentTransaction.order_id == order_id,
            PaymentTransaction.status == PaymentStatus.SUCCESS,
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


def find_overdue_pending(
    db: Session,
    now: datetime,
    limit: int | None = None,
) -> list[PaymentTransaction]:
    statement = (
        select(PaymentTransaction)
        .where(
            PaymentTransaction.status == PaymentStatus.PENDING,
            PaymentTransaction.expire_at <= now,
        )
        .order_by(PaymentTransaction.expire_at.asc(), PaymentTransaction.created_at.asc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    return list(
        db.scalars(statement).all()
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
    qr_reference: str | None,
    qr_content: str,
    qr_image_base64: str | None,
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
        qr_reference=qr_reference,
        qr_content=qr_content,
        qr_image_base64=qr_image_base64,
        expire_at=expire_at,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    db.flush()
    return payment


def save(
    db: Session,
    payment: PaymentTransaction,
) -> PaymentTransaction:
    db.add(payment)
    db.flush()
    return payment
