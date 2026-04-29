from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order_reference import OrderReference


def get_by_merchant_and_order(
    db: Session,
    merchant_db_id: UUID,
    order_id: str,
) -> OrderReference | None:
    return db.scalar(
        select(OrderReference).where(
            OrderReference.merchant_db_id == merchant_db_id,
            OrderReference.order_id == order_id,
        )
    )


def create(
    db: Session,
    merchant_db_id: UUID,
    order_id: str,
) -> OrderReference:
    order_reference = OrderReference(
        merchant_db_id=merchant_db_id,
        order_id=order_id,
    )
    db.add(order_reference)
    db.flush()
    return order_reference


def set_latest_payment(
    db: Session,
    order_reference: OrderReference,
    payment_transaction_id: UUID,
) -> OrderReference:
    order_reference.latest_payment_transaction_id = payment_transaction_id
    db.add(order_reference)
    db.flush()
    return order_reference
