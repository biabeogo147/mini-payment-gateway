from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utc_now
from app.models.enums import PaymentStatus, QrProvider
from app.models.payment_transaction import PaymentTransaction
from app.repositories import merchant_qr_account_repository, order_reference_repository, payment_repository
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.payment import CreatePaymentRequest, PaymentResponse, PaymentStatusResponse
from app.services.merchant_readiness_service import assert_can_create_payment
from app.services.qr_service import generate_qr_reference, generate_vietqr_payment_qr


def create_payment(
    db: Session,
    authenticated_merchant: AuthenticatedMerchant,
    request: CreatePaymentRequest,
    idempotency_key: str | None,
    now: datetime | None = None,
) -> PaymentResponse:
    merchant = authenticated_merchant.merchant
    assert_can_create_payment(merchant)
    _assert_vietqr_supported_amount(request)

    normalized_now = now or utc_now()
    expire_at = request.resolve_expire_at(normalized_now)

    pending_payment = payment_repository.get_pending_by_merchant_order(
        db,
        merchant.id,
        request.order_id,
    )
    if pending_payment is not None:
        if _is_semantically_identical(pending_payment, request, expire_at):
            return PaymentResponse.from_payment(pending_payment, authenticated_merchant.merchant_id)
        raise AppError(
            error_code="PAYMENT_PENDING_EXISTS",
            message="A pending payment already exists for this order.",
            status_code=409,
            details={"order_id": request.order_id, "transaction_id": pending_payment.transaction_id},
        )

    latest_payment = payment_repository.get_latest_by_merchant_order(
        db,
        merchant.id,
        request.order_id,
    )
    if latest_payment is not None and latest_payment.status == PaymentStatus.SUCCESS:
        raise AppError(
            error_code="PAYMENT_ALREADY_SUCCESS",
            message="A successful payment already exists for this order.",
            status_code=409,
            details={"order_id": request.order_id, "transaction_id": latest_payment.transaction_id},
        )

    order_reference = order_reference_repository.get_by_merchant_and_order(db, merchant.id, request.order_id)
    if order_reference is None:
        order_reference = order_reference_repository.create(db, merchant.id, request.order_id)

    transaction_id = _new_transaction_id()
    qr_account = merchant_qr_account_repository.get_active_by_merchant_provider(
        db,
        merchant.id,
        QrProvider.VIETQR,
    )
    if qr_account is None:
        raise AppError(
            error_code="ACTIVE_QR_ACCOUNT_REQUIRED",
            message="An active QR receiving account is required before creating VietQR payments.",
            status_code=409,
            details={"merchant_id": authenticated_merchant.merchant_id, "provider": QrProvider.VIETQR.value},
        )
    qr_reference = generate_qr_reference(transaction_id)
    generated_qr = generate_vietqr_payment_qr(
        qr_account=qr_account,
        amount=request.amount,
        qr_reference=qr_reference,
    )
    payment = payment_repository.create(
        db,
        transaction_id=transaction_id,
        merchant_db_id=merchant.id,
        order_reference_id=order_reference.id,
        order_id=request.order_id,
        amount=request.amount,
        currency=request.currency,
        description=request.description,
        qr_reference=qr_reference,
        qr_content=generated_qr.qr_content,
        qr_image_base64=generated_qr.qr_image_base64,
        expire_at=expire_at,
        idempotency_key=idempotency_key,
    )
    order_reference_repository.set_latest_payment(db, order_reference, payment.id)
    db.commit()
    return PaymentResponse.from_payment(payment, authenticated_merchant.merchant_id)


def get_payment_by_transaction_id(
    db: Session,
    authenticated_merchant: AuthenticatedMerchant,
    transaction_id: str,
) -> PaymentStatusResponse:
    payment = payment_repository.get_by_transaction_id(db, transaction_id)
    if payment is None or payment.merchant_db_id != authenticated_merchant.merchant.id:
        raise _payment_not_found(transaction_id=transaction_id)
    return PaymentStatusResponse.from_payment(payment, authenticated_merchant.merchant_id)


def get_payment_by_order_id(
    db: Session,
    authenticated_merchant: AuthenticatedMerchant,
    order_id: str,
) -> PaymentStatusResponse:
    payment = payment_repository.get_latest_by_merchant_order(
        db,
        authenticated_merchant.merchant.id,
        order_id,
    )
    if payment is None:
        raise _payment_not_found(order_id=order_id)
    return PaymentStatusResponse.from_payment(payment, authenticated_merchant.merchant_id)


def _is_semantically_identical(
    payment: PaymentTransaction,
    request: CreatePaymentRequest,
    expire_at: datetime,
) -> bool:
    return (
        Decimal(payment.amount) == request.amount
        and payment.currency == request.currency
        and payment.description == request.description
        and payment.expire_at == expire_at
    )


def _new_transaction_id() -> str:
    return f"pay_{uuid4().hex}"


def _assert_vietqr_supported_amount(request: CreatePaymentRequest) -> None:
    if request.currency != "VND" or request.amount != request.amount.to_integral_value():
        raise AppError(
            error_code="VIETQR_REQUIRES_WHOLE_VND",
            message="VietQR pilot payments require whole VND amounts.",
            status_code=422,
            details={"currency": request.currency, "amount": str(request.amount)},
        )


def _payment_not_found(**details: str) -> AppError:
    return AppError(
        error_code="PAYMENT_NOT_FOUND",
        message="Payment not found.",
        status_code=404,
        details=details,
    )
