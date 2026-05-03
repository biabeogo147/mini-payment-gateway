from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.enums import EntityType, ReconciliationStatus
from app.models.payment_transaction import PaymentTransaction
from app.models.reconciliation_record import ReconciliationRecord


def create_payment_reconciliation_record(
    db: Session,
    payment: PaymentTransaction,
    external_status: str,
    external_amount: Decimal,
    match_result: ReconciliationStatus,
    mismatch_reason_code: str | None = None,
    mismatch_reason_message: str | None = None,
) -> ReconciliationRecord:
    record = ReconciliationRecord(
        entity_type=EntityType.PAYMENT,
        entity_id=payment.id,
        internal_status=payment.status.value,
        external_status=external_status,
        internal_amount=Decimal(payment.amount),
        external_amount=external_amount,
        match_result=match_result,
        mismatch_reason_code=mismatch_reason_code,
        mismatch_reason_message=mismatch_reason_message,
    )
    db.add(record)
    db.flush()
    return record
