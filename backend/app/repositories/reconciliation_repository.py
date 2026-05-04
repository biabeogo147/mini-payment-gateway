from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import internal_user as _internal_user  # noqa: F401
from app.models.enums import EntityType, ReconciliationStatus
from app.models.payment_transaction import PaymentTransaction
from app.models.reconciliation_record import ReconciliationRecord
from app.models.refund_transaction import RefundTransaction


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


def create_refund_reconciliation_record(
    db: Session,
    refund: RefundTransaction,
    external_status: str,
    external_amount: Decimal,
    match_result: ReconciliationStatus,
    mismatch_reason_code: str | None = None,
    mismatch_reason_message: str | None = None,
) -> ReconciliationRecord:
    record = ReconciliationRecord(
        entity_type=EntityType.REFUND,
        entity_id=refund.id,
        internal_status=refund.status.value,
        external_status=external_status,
        internal_amount=Decimal(refund.refund_amount),
        external_amount=external_amount,
        match_result=match_result,
        mismatch_reason_code=mismatch_reason_code,
        mismatch_reason_message=mismatch_reason_message,
    )
    db.add(record)
    db.flush()
    return record


def get_by_id(
    db: Session,
    record_id: UUID,
) -> ReconciliationRecord | None:
    return db.scalar(select(ReconciliationRecord).where(ReconciliationRecord.id == record_id))


def find(
    db: Session,
    match_result: ReconciliationStatus | None = None,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    limit: int = 100,
) -> list[ReconciliationRecord]:
    statement = select(ReconciliationRecord)
    if match_result is not None:
        statement = statement.where(ReconciliationRecord.match_result == match_result)
    if entity_type is not None:
        statement = statement.where(ReconciliationRecord.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(ReconciliationRecord.entity_id == entity_id)
    statement = statement.order_by(ReconciliationRecord.created_at.desc(), ReconciliationRecord.id.desc()).limit(limit)
    return list(db.scalars(statement).all())


def save(
    db: Session,
    record: ReconciliationRecord,
) -> ReconciliationRecord:
    db.add(record)
    db.flush()
    return record
