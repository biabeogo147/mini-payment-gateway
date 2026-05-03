from datetime import datetime

from app.core.errors import AppError
from app.models.enums import PaymentStatus
from app.models.payment_transaction import PaymentTransaction


ALLOWED_TRANSITIONS = {
    PaymentStatus.PENDING: {
        PaymentStatus.SUCCESS,
        PaymentStatus.FAILED,
        PaymentStatus.EXPIRED,
    }
}


def assert_payment_transition_allowed(
    current_status: PaymentStatus,
    target_status: PaymentStatus,
) -> None:
    if target_status in ALLOWED_TRANSITIONS.get(current_status, set()):
        return
    raise AppError(
        error_code="PAYMENT_INVALID_STATE_TRANSITION",
        message="Payment state transition is not allowed.",
        status_code=409,
        details={
            "current_status": current_status.value,
            "target_status": target_status.value,
        },
    )


def mark_success(
    payment: PaymentTransaction,
    paid_at: datetime,
    external_reference: str | None = None,
) -> PaymentTransaction:
    assert_payment_transition_allowed(payment.status, PaymentStatus.SUCCESS)
    payment.status = PaymentStatus.SUCCESS
    payment.paid_at = paid_at
    payment.external_reference = external_reference
    return payment


def mark_failed(
    payment: PaymentTransaction,
    reason_code: str,
    reason_message: str | None = None,
    external_reference: str | None = None,
) -> PaymentTransaction:
    assert_payment_transition_allowed(payment.status, PaymentStatus.FAILED)
    payment.status = PaymentStatus.FAILED
    payment.failed_reason_code = reason_code
    payment.failed_reason_message = reason_message
    payment.external_reference = external_reference
    return payment


def mark_expired(payment: PaymentTransaction) -> PaymentTransaction:
    assert_payment_transition_allowed(payment.status, PaymentStatus.EXPIRED)
    payment.status = PaymentStatus.EXPIRED
    return payment
