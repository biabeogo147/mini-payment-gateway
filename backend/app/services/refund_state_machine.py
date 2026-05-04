from datetime import datetime

from app.core.errors import AppError
from app.models.enums import RefundStatus
from app.models.refund_transaction import RefundTransaction


def assert_refund_transition_allowed(
    current_status: RefundStatus,
    target_status: RefundStatus,
) -> None:
    if current_status == RefundStatus.REFUND_PENDING and target_status in {
        RefundStatus.REFUNDED,
        RefundStatus.REFUND_FAILED,
    }:
        return
    raise AppError(
        error_code="REFUND_INVALID_STATE_TRANSITION",
        message="Refund state transition is not allowed.",
        status_code=409,
        details={"current_status": current_status.value, "target_status": target_status.value},
    )


def mark_refunded(
    refund: RefundTransaction,
    processed_at: datetime,
    external_reference: str | None = None,
) -> RefundTransaction:
    assert_refund_transition_allowed(refund.status, RefundStatus.REFUNDED)
    refund.status = RefundStatus.REFUNDED
    refund.processed_at = processed_at
    refund.external_reference = external_reference
    return refund


def mark_refund_failed(
    refund: RefundTransaction,
    reason_code: str,
    reason_message: str | None = None,
    external_reference: str | None = None,
    processed_at: datetime | None = None,
) -> RefundTransaction:
    assert_refund_transition_allowed(refund.status, RefundStatus.REFUND_FAILED)
    refund.status = RefundStatus.REFUND_FAILED
    refund.failed_reason_code = reason_code
    refund.failed_reason_message = reason_message
    refund.processed_at = processed_at
    refund.external_reference = external_reference
    return refund
