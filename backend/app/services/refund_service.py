from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utc_now
from app.models.enums import PaymentStatus, RefundStatus
from app.models.payment_transaction import PaymentTransaction
from app.models.refund_transaction import RefundTransaction
from app.repositories import payment_repository, refund_repository
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.refund import CreateRefundRequest, RefundResponse, RefundStatusResponse
from app.services.merchant_readiness_service import assert_can_create_refund

REFUND_WINDOW = timedelta(days=7)


def create_refund(
    db: Session,
    authenticated_merchant: AuthenticatedMerchant,
    request: CreateRefundRequest,
    idempotency_key: str | None,
    now: datetime | None = None,
) -> RefundResponse:
    merchant = authenticated_merchant.merchant
    assert_can_create_refund(merchant)

    payment = _resolve_original_payment(db, merchant.id, request)
    _assert_payment_refundable(payment)
    _assert_full_refund(payment, request)
    _assert_refund_window(payment, now or utc_now())

    existing_refund = refund_repository.get_by_merchant_refund_id(db, merchant.id, request.refund_id)
    if existing_refund is not None:
        if _is_semantically_identical(existing_refund, payment, request):
            return RefundResponse.from_refund(existing_refund, payment)
        raise _refund_not_allowed(
            "A refund with this refund id already exists with different details.",
            refund_id=request.refund_id,
        )

    active_refund = refund_repository.get_by_payment_and_statuses(
        db,
        payment.id,
        (RefundStatus.REFUND_PENDING, RefundStatus.REFUNDED),
    )
    if active_refund is not None:
        raise _refund_not_allowed(
            "An active or successful refund already exists for this payment.",
            transaction_id=payment.transaction_id,
            refund_transaction_id=active_refund.refund_transaction_id,
            refund_status=active_refund.status.value,
        )

    refund = refund_repository.create(
        db=db,
        refund_transaction_id=_new_refund_transaction_id(),
        merchant_db_id=merchant.id,
        payment_transaction_id=payment.id,
        refund_id=request.refund_id,
        refund_amount=request.refund_amount,
        reason=request.reason,
        idempotency_key=idempotency_key,
    )
    db.commit()
    return RefundResponse.from_refund(refund, payment)


def get_refund_by_transaction_id(
    db: Session,
    authenticated_merchant: AuthenticatedMerchant,
    refund_transaction_id: str,
) -> RefundStatusResponse:
    refund = refund_repository.get_by_refund_transaction_id(db, refund_transaction_id)
    if refund is None or refund.merchant_db_id != authenticated_merchant.merchant.id:
        raise _refund_not_found(refund_transaction_id=refund_transaction_id)

    payment = payment_repository.get_by_id(db, refund.payment_transaction_id)
    if payment is None:
        raise _refund_not_found(refund_transaction_id=refund_transaction_id)
    return RefundStatusResponse.from_refund(refund, payment)


def get_refund_by_refund_id(
    db: Session,
    authenticated_merchant: AuthenticatedMerchant,
    refund_id: str,
) -> RefundStatusResponse:
    refund = refund_repository.get_by_merchant_refund_id(db, authenticated_merchant.merchant.id, refund_id)
    if refund is None:
        raise _refund_not_found(refund_id=refund_id)

    payment = payment_repository.get_by_id(db, refund.payment_transaction_id)
    if payment is None:
        raise _refund_not_found(refund_id=refund_id)
    return RefundStatusResponse.from_refund(refund, payment)


def _resolve_original_payment(
    db: Session,
    merchant_db_id,
    request: CreateRefundRequest,
) -> PaymentTransaction:
    if request.original_transaction_id is not None:
        payment = payment_repository.get_by_transaction_id(db, request.original_transaction_id)
        if payment is None or payment.merchant_db_id != merchant_db_id:
            raise _payment_not_found(transaction_id=request.original_transaction_id)
        return payment

    payment = payment_repository.get_success_by_merchant_order(db, merchant_db_id, request.order_id or "")
    if payment is None:
        raise _payment_not_found(order_id=request.order_id or "")
    return payment


def _assert_payment_refundable(payment: PaymentTransaction) -> None:
    if payment.status == PaymentStatus.SUCCESS and payment.paid_at is not None:
        return
    raise AppError(
        error_code="PAYMENT_NOT_REFUNDABLE",
        message="Payment is not refundable.",
        status_code=409,
        details={"transaction_id": payment.transaction_id, "payment_status": payment.status.value},
    )


def _assert_full_refund(
    payment: PaymentTransaction,
    request: CreateRefundRequest,
) -> None:
    if Decimal(payment.amount) == request.refund_amount:
        return
    raise AppError(
        error_code="REFUND_AMOUNT_NOT_FULL",
        message="Refund amount must match the original payment amount.",
        status_code=409,
        details={
            "transaction_id": payment.transaction_id,
            "payment_amount": str(payment.amount),
            "refund_amount": str(request.refund_amount),
        },
    )


def _assert_refund_window(
    payment: PaymentTransaction,
    now: datetime,
) -> None:
    paid_at = _ensure_timezone(payment.paid_at)
    normalized_now = _ensure_timezone(now)
    if normalized_now <= paid_at + REFUND_WINDOW:
        return
    raise AppError(
        error_code="REFUND_WINDOW_EXPIRED",
        message="Refund window has expired.",
        status_code=409,
        details={"transaction_id": payment.transaction_id, "paid_at": paid_at.isoformat()},
    )


def _is_semantically_identical(
    refund: RefundTransaction,
    payment: PaymentTransaction,
    request: CreateRefundRequest,
) -> bool:
    return (
        refund.payment_transaction_id == payment.id
        and Decimal(refund.refund_amount) == request.refund_amount
        and refund.reason == request.reason
    )


def _ensure_timezone(value: datetime | None) -> datetime:
    if value is None:
        raise ValueError("datetime is required")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _new_refund_transaction_id() -> str:
    return f"rfnd_{uuid4().hex}"


def _payment_not_found(**details: str) -> AppError:
    return AppError(
        error_code="PAYMENT_NOT_FOUND",
        message="Payment not found.",
        status_code=404,
        details=details,
    )


def _refund_not_found(**details: str) -> AppError:
    return AppError(
        error_code="REFUND_NOT_FOUND",
        message="Refund not found.",
        status_code=404,
        details=details,
    )


def _refund_not_allowed(message: str, **details: str) -> AppError:
    return AppError(
        error_code="REFUND_NOT_ALLOWED",
        message=message,
        status_code=409,
        details=details,
    )
