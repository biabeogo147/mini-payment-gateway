from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.enums import EntityType, PaymentStatus, RefundStatus
from app.models.payment_transaction import PaymentTransaction
from app.models.refund_transaction import RefundTransaction
from app.models.webhook_event import WebhookEvent
from app.repositories import merchant_repository, payment_repository, webhook_repository

_PAYMENT_EVENT_TYPES = {
    PaymentStatus.SUCCESS: "payment.succeeded",
    PaymentStatus.FAILED: "payment.failed",
    PaymentStatus.EXPIRED: "payment.expired",
}

_REFUND_EVENT_TYPES = {
    RefundStatus.REFUNDED: "refund.succeeded",
    RefundStatus.REFUND_FAILED: "refund.failed",
}


def create_payment_event_if_needed(
    db: Session,
    payment: PaymentTransaction,
    now: datetime | None = None,
) -> WebhookEvent | None:
    event_type = _PAYMENT_EVENT_TYPES.get(payment.status)
    if event_type is None:
        return None

    merchant = merchant_repository.get_by_id(db, payment.merchant_db_id)
    if merchant is None or not merchant.webhook_url:
        return None

    existing_event = webhook_repository.get_existing_event(
        db=db,
        merchant_db_id=merchant.id,
        event_type=event_type,
        entity_type=EntityType.PAYMENT,
        entity_id=payment.id,
    )
    if existing_event is not None:
        return existing_event

    occurred_at = now or utc_now()
    event_id = _new_event_id()
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "merchant_id": merchant.merchant_id,
        "entity_type": EntityType.PAYMENT.value,
        "entity_id": str(payment.id),
        "created_at": _isoformat(occurred_at),
        "data": {
            "transaction_id": payment.transaction_id,
            "order_id": payment.order_id,
            "amount": _decimal_string(payment.amount),
            "currency": payment.currency,
            "status": payment.status.value,
            "paid_at": _isoformat(payment.paid_at),
            "expire_at": _isoformat(payment.expire_at),
            "external_reference": payment.external_reference,
            "failed_reason_code": payment.failed_reason_code,
            "failed_reason_message": payment.failed_reason_message,
        },
    }
    return webhook_repository.create_event(
        db=db,
        event_id=event_id,
        merchant_db_id=merchant.id,
        event_type=event_type,
        entity_type=EntityType.PAYMENT,
        entity_id=payment.id,
        payload_json=payload,
        next_retry_at=occurred_at,
    )


def create_refund_event_if_needed(
    db: Session,
    refund: RefundTransaction,
    now: datetime | None = None,
) -> WebhookEvent | None:
    event_type = _REFUND_EVENT_TYPES.get(refund.status)
    if event_type is None:
        return None

    merchant = merchant_repository.get_by_id(db, refund.merchant_db_id)
    if merchant is None or not merchant.webhook_url:
        return None

    payment = payment_repository.get_by_id(db, refund.payment_transaction_id)
    if payment is None:
        return None

    existing_event = webhook_repository.get_existing_event(
        db=db,
        merchant_db_id=merchant.id,
        event_type=event_type,
        entity_type=EntityType.REFUND,
        entity_id=refund.id,
    )
    if existing_event is not None:
        return existing_event

    occurred_at = now or utc_now()
    event_id = _new_event_id()
    payload = {
        "event_id": event_id,
        "event_type": event_type,
        "merchant_id": merchant.merchant_id,
        "entity_type": EntityType.REFUND.value,
        "entity_id": str(refund.id),
        "created_at": _isoformat(occurred_at),
        "data": {
            "refund_transaction_id": refund.refund_transaction_id,
            "refund_id": refund.refund_id,
            "original_transaction_id": payment.transaction_id,
            "order_id": payment.order_id,
            "refund_amount": _decimal_string(refund.refund_amount),
            "currency": payment.currency,
            "status": refund.status.value,
            "processed_at": _isoformat(refund.processed_at),
            "external_reference": refund.external_reference,
            "failed_reason_code": refund.failed_reason_code,
            "failed_reason_message": refund.failed_reason_message,
        },
    }
    return webhook_repository.create_event(
        db=db,
        event_id=event_id,
        merchant_db_id=merchant.id,
        event_type=event_type,
        entity_type=EntityType.REFUND,
        entity_id=refund.id,
        payload_json=payload,
        next_retry_at=occurred_at,
    )


def _new_event_id() -> str:
    return f"evt_{uuid4().hex}"


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal_string(value: Decimal) -> str:
    return str(Decimal(value))
