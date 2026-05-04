from datetime import datetime

from sqlalchemy.orm import Session

from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import CallbackProcessingResult, CallbackSourceType, CallbackType


def create_payment_callback_log(
    db: Session,
    source_type: CallbackSourceType,
    external_reference: str | None,
    transaction_reference: str | None,
    raw_payload: dict,
    normalized_status: str | None,
    received_at: datetime,
    processed_at: datetime | None,
    processing_result: CallbackProcessingResult,
    error_message: str | None = None,
) -> BankCallbackLog:
    log = BankCallbackLog(
        source_type=source_type,
        external_reference=external_reference,
        transaction_reference=transaction_reference,
        callback_type=CallbackType.PAYMENT_RESULT,
        raw_payload_json=raw_payload,
        normalized_status=normalized_status,
        received_at=received_at,
        processed_at=processed_at,
        processing_result=processing_result,
        error_message=error_message,
    )
    db.add(log)
    db.flush()
    return log


def create_refund_callback_log(
    db: Session,
    source_type: CallbackSourceType,
    external_reference: str | None,
    transaction_reference: str | None,
    raw_payload: dict,
    normalized_status: str | None,
    received_at: datetime,
    processed_at: datetime | None,
    processing_result: CallbackProcessingResult,
    error_message: str | None = None,
) -> BankCallbackLog:
    log = BankCallbackLog(
        source_type=source_type,
        external_reference=external_reference,
        transaction_reference=transaction_reference,
        callback_type=CallbackType.REFUND_RESULT,
        raw_payload_json=raw_payload,
        normalized_status=normalized_status,
        received_at=received_at,
        processed_at=processed_at,
        processing_result=processing_result,
        error_message=error_message,
    )
    db.add(log)
    db.flush()
    return log
