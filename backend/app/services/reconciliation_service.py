from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utc_now
from app.models.enums import EntityType, PaymentStatus, ReconciliationStatus, RefundStatus
from app.models.payment_transaction import PaymentTransaction
from app.models.reconciliation_record import ReconciliationRecord
from app.models.refund_transaction import RefundTransaction
from app.repositories import reconciliation_repository
from app.schemas.ops import OpsActorContext
from app.schemas.reconciliation import ReconciliationRecordResponse, ResolveReconciliationRequest
from app.services import audit_service


def create_payment_evidence(
    db: Session,
    payment: PaymentTransaction,
    external_status: str,
    external_amount: Decimal,
    now: datetime | None = None,
) -> ReconciliationRecord:
    match_result, reason_code, reason_message = _classify_payment_evidence(
        payment=payment,
        external_status=external_status,
        external_amount=external_amount,
    )
    record = reconciliation_repository.create_payment_reconciliation_record(
        db=db,
        payment=payment,
        external_status=external_status,
        external_amount=external_amount,
        match_result=match_result,
        mismatch_reason_code=reason_code,
        mismatch_reason_message=reason_message,
    )
    db.commit()
    return record


def create_refund_evidence(
    db: Session,
    refund: RefundTransaction,
    external_status: str,
    external_amount: Decimal,
    now: datetime | None = None,
) -> ReconciliationRecord:
    match_result, reason_code, reason_message = _classify_refund_evidence(
        refund=refund,
        external_status=external_status,
        external_amount=external_amount,
    )
    record = reconciliation_repository.create_refund_reconciliation_record(
        db=db,
        refund=refund,
        external_status=external_status,
        external_amount=external_amount,
        match_result=match_result,
        mismatch_reason_code=reason_code,
        mismatch_reason_message=reason_message,
    )
    db.commit()
    return record


def list_records(
    db: Session,
    match_result: ReconciliationStatus | None = None,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    limit: int = 100,
) -> list[ReconciliationRecordResponse]:
    records = reconciliation_repository.find(
        db=db,
        match_result=match_result,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return [ReconciliationRecordResponse.from_record(record) for record in records]


def get_record(
    db: Session,
    record_id: UUID,
) -> ReconciliationRecordResponse:
    record = reconciliation_repository.get_by_id(db, record_id)
    if record is None:
        raise AppError(
            error_code="RECONCILIATION_NOT_FOUND",
            message="Reconciliation record not found.",
            status_code=404,
            details={"record_id": str(record_id)},
        )
    return ReconciliationRecordResponse.from_record(record)


def resolve_record(
    db: Session,
    record_id: UUID,
    request: ResolveReconciliationRequest,
    actor: OpsActorContext,
    now: datetime | None = None,
) -> ReconciliationRecordResponse:
    reviewed_at = now or utc_now()
    record = reconciliation_repository.get_by_id(db, record_id)
    if record is None:
        raise AppError(
            error_code="RECONCILIATION_NOT_FOUND",
            message="Reconciliation record not found.",
            status_code=404,
            details={"record_id": str(record_id)},
        )
    if record.match_result == ReconciliationStatus.RESOLVED:
        raise AppError(
            error_code="RECONCILIATION_ALREADY_RESOLVED",
            message="Reconciliation record is already resolved.",
            status_code=409,
            details={"record_id": str(record_id)},
        )

    before_state = _record_state(record)
    record.match_result = ReconciliationStatus.RESOLVED
    record.reviewed_by = request.reviewed_by or actor.actor_id
    record.review_note = request.review_note
    record.updated_at = reviewed_at
    reconciliation_repository.save(db, record)
    audit_service.record_event(
        db=db,
        event_type="RECONCILIATION_RESOLVED",
        entity_type=EntityType.RECONCILIATION,
        entity_id=record.id,
        actor_type=actor.actor_type,
        actor_id=actor.actor_id,
        before_state=before_state,
        after_state=_record_state(record),
        reason=actor.reason,
    )
    db.commit()
    return ReconciliationRecordResponse.from_record(record)


def _classify_payment_evidence(
    payment: PaymentTransaction,
    external_status: str,
    external_amount: Decimal,
) -> tuple[ReconciliationStatus, str | None, str | None]:
    if Decimal(payment.amount) != external_amount:
        return (
            ReconciliationStatus.MISMATCHED,
            "AMOUNT_MISMATCH",
            "External payment amount does not match internal amount.",
        )
    if payment.status == PaymentStatus.EXPIRED and external_status == PaymentStatus.SUCCESS.value:
        return (
            ReconciliationStatus.PENDING_REVIEW,
            "LATE_SUCCESS_AFTER_EXPIRATION",
            "External success arrived after the payment expired internally.",
        )
    if payment.status.value != external_status:
        return (
            ReconciliationStatus.MISMATCHED,
            "STATUS_MISMATCH",
            "External payment status does not match internal status.",
        )
    return ReconciliationStatus.MATCHED, None, None


def _classify_refund_evidence(
    refund: RefundTransaction,
    external_status: str,
    external_amount: Decimal,
) -> tuple[ReconciliationStatus, str | None, str | None]:
    if Decimal(refund.refund_amount) != external_amount:
        return (
            ReconciliationStatus.MISMATCHED,
            "AMOUNT_MISMATCH",
            "External refund amount does not match internal amount.",
        )
    expected_internal_status = _refund_internal_status_for_external(external_status)
    if expected_internal_status is None or refund.status != expected_internal_status:
        return (
            ReconciliationStatus.PENDING_REVIEW,
            "STATUS_CONFLICT",
            "External refund status conflicts with current internal state.",
        )
    return ReconciliationStatus.MATCHED, None, None


def _refund_internal_status_for_external(external_status: str) -> RefundStatus | None:
    if external_status == "SUCCESS":
        return RefundStatus.REFUNDED
    if external_status == "FAILED":
        return RefundStatus.REFUND_FAILED
    return None


def _record_state(record: ReconciliationRecord) -> dict:
    return {
        "id": str(record.id),
        "entity_type": record.entity_type.value,
        "entity_id": str(record.entity_id),
        "internal_status": record.internal_status,
        "external_status": record.external_status,
        "internal_amount": str(record.internal_amount),
        "external_amount": str(record.external_amount),
        "match_result": record.match_result.value,
        "mismatch_reason_code": record.mismatch_reason_code,
        "mismatch_reason_message": record.mismatch_reason_message,
        "reviewed_by": str(record.reviewed_by) if record.reviewed_by else None,
        "review_note": record.review_note,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
