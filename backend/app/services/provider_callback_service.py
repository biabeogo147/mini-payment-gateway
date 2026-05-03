from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.enums import CallbackProcessingResult, PaymentStatus, ReconciliationStatus
from app.models.payment_transaction import PaymentTransaction
from app.repositories import bank_callback_repository, payment_repository, reconciliation_repository
from app.schemas.provider_callback import (
    PaymentCallbackRequest,
    PaymentCallbackResponse,
    PaymentCallbackStatus,
)
from app.services import payment_state_machine


def process_payment_callback(
    db: Session,
    request: PaymentCallbackRequest,
    now: datetime | None = None,
) -> PaymentCallbackResponse:
    processed_at = now or utc_now()
    payment = payment_repository.get_by_transaction_id(db, request.transaction_reference)

    if payment is None:
        _log_callback(
            db,
            request,
            processed_at,
            CallbackProcessingResult.PENDING_REVIEW,
            error_message="Payment transaction was not found.",
        )
        db.commit()
        return PaymentCallbackResponse(
            transaction_id=None,
            status=None,
            processing_result=CallbackProcessingResult.PENDING_REVIEW,
        )

    if Decimal(payment.amount) != request.amount:
        record = reconciliation_repository.create_payment_reconciliation_record(
            db=db,
            payment=payment,
            external_status=request.status.value,
            external_amount=request.amount,
            match_result=ReconciliationStatus.MISMATCHED,
            mismatch_reason_code="AMOUNT_MISMATCH",
            mismatch_reason_message="Callback amount does not match payment amount.",
        )
        _log_callback(
            db,
            request,
            processed_at,
            CallbackProcessingResult.PENDING_REVIEW,
            error_message="Callback amount does not match payment amount.",
        )
        db.commit()
        return _response(payment, CallbackProcessingResult.PENDING_REVIEW, record)

    target_status = _target_payment_status(request.status)
    if payment.status == target_status:
        _log_callback(db, request, processed_at, CallbackProcessingResult.IGNORED)
        db.commit()
        return _response(payment, CallbackProcessingResult.IGNORED)

    if payment.status != PaymentStatus.PENDING:
        reason_code = _conflict_reason_code(payment.status, target_status)
        record = reconciliation_repository.create_payment_reconciliation_record(
            db=db,
            payment=payment,
            external_status=request.status.value,
            external_amount=request.amount,
            match_result=ReconciliationStatus.PENDING_REVIEW,
            mismatch_reason_code=reason_code,
            mismatch_reason_message="Callback conflicts with current payment final state.",
        )
        _log_callback(
            db,
            request,
            processed_at,
            CallbackProcessingResult.PENDING_REVIEW,
            error_message="Callback conflicts with current payment final state.",
        )
        db.commit()
        return _response(payment, CallbackProcessingResult.PENDING_REVIEW, record)

    if request.status == PaymentCallbackStatus.SUCCESS:
        payment_state_machine.mark_success(
            payment,
            paid_at=request.paid_at or processed_at,
            external_reference=request.external_reference,
        )
    else:
        payment_state_machine.mark_failed(
            payment,
            reason_code=request.failed_reason_code or "PROVIDER_FAILED",
            reason_message=request.failed_reason_message,
            external_reference=request.external_reference,
        )

    payment_repository.save(db, payment)
    _log_callback(db, request, processed_at, CallbackProcessingResult.PROCESSED)
    db.commit()
    return _response(payment, CallbackProcessingResult.PROCESSED)


def _log_callback(
    db: Session,
    request: PaymentCallbackRequest,
    processed_at: datetime,
    processing_result: CallbackProcessingResult,
    error_message: str | None = None,
):
    return bank_callback_repository.create_payment_callback_log(
        db=db,
        source_type=request.source_type,
        external_reference=request.external_reference,
        transaction_reference=request.transaction_reference,
        raw_payload=request.raw_payload,
        normalized_status=request.status.value,
        received_at=processed_at,
        processed_at=processed_at,
        processing_result=processing_result,
        error_message=error_message,
    )


def _target_payment_status(callback_status: PaymentCallbackStatus) -> PaymentStatus:
    if callback_status == PaymentCallbackStatus.SUCCESS:
        return PaymentStatus.SUCCESS
    return PaymentStatus.FAILED


def _conflict_reason_code(
    current_status: PaymentStatus,
    target_status: PaymentStatus,
) -> str:
    if current_status == PaymentStatus.EXPIRED and target_status == PaymentStatus.SUCCESS:
        return "LATE_SUCCESS_AFTER_EXPIRATION"
    return "STATUS_CONFLICT"


def _response(
    payment: PaymentTransaction,
    processing_result: CallbackProcessingResult,
    reconciliation_record=None,
) -> PaymentCallbackResponse:
    return PaymentCallbackResponse(
        transaction_id=payment.transaction_id,
        status=payment.status,
        processing_result=processing_result,
        reconciliation_record_id=str(reconciliation_record.id) if reconciliation_record is not None else None,
    )
