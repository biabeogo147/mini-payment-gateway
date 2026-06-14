from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import (
    CallbackType,
    EntityType,
    MerchantStatus,
    OnboardingCaseStatus,
    PaymentStatus,
    ReconciliationStatus,
    RefundStatus,
    WebhookEventStatus,
)
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_onboarding_case import MerchantOnboardingCase
from app.models.payment_transaction import PaymentTransaction
from app.models.reconciliation_record import ReconciliationRecord
from app.models.refund_transaction import RefundTransaction
from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.models.webhook_event import WebhookEvent


def list_merchants(
    db: Session,
    *,
    search: str | None = None,
    status: MerchantStatus | None = None,
    onboarding_status: OnboardingCaseStatus | None = None,
    limit: int = 100,
) -> list[tuple[Merchant, MerchantOnboardingCase | None]]:
    stmt = (
        select(Merchant, MerchantOnboardingCase)
        .outerjoin(
            MerchantOnboardingCase,
            MerchantOnboardingCase.merchant_db_id == Merchant.id,
        )
        .order_by(Merchant.created_at.desc(), Merchant.merchant_id.asc())
        .limit(limit)
    )
    if search:
        pattern = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Merchant.merchant_id).like(pattern),
                func.lower(Merchant.merchant_name).like(pattern),
                func.lower(Merchant.contact_email).like(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(Merchant.status == status)
    if onboarding_status is not None:
        stmt = stmt.where(MerchantOnboardingCase.status == onboarding_status)
    return list(db.execute(stmt).all())


def get_merchant_bundle(
    db: Session,
    *,
    merchant_id: str,
) -> tuple[Merchant, MerchantOnboardingCase | None] | None:
    row = db.execute(
        select(Merchant, MerchantOnboardingCase)
        .outerjoin(
            MerchantOnboardingCase,
            MerchantOnboardingCase.merchant_db_id == Merchant.id,
        )
        .where(Merchant.merchant_id == merchant_id)
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def list_credentials_for_merchant(db: Session, merchant_db_id: UUID) -> list[MerchantCredential]:
    return list(
        db.scalars(
            select(MerchantCredential)
            .where(MerchantCredential.merchant_db_id == merchant_db_id)
            .order_by(MerchantCredential.created_at.desc())
        ).all()
    )


def list_payments(
    db: Session,
    *,
    transaction_id: str | None = None,
    order_id: str | None = None,
    merchant_id: str | None = None,
    status=None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> list[tuple[PaymentTransaction, Merchant]]:
    stmt = (
        select(PaymentTransaction, Merchant)
        .join(Merchant, Merchant.id == PaymentTransaction.merchant_db_id)
        .order_by(PaymentTransaction.created_at.desc(), PaymentTransaction.transaction_id.asc())
        .limit(limit)
    )
    if transaction_id:
        stmt = stmt.where(PaymentTransaction.transaction_id.like(f"%{transaction_id.strip()}%"))
    if order_id:
        stmt = stmt.where(PaymentTransaction.order_id.like(f"%{order_id.strip()}%"))
    if merchant_id:
        stmt = stmt.where(Merchant.merchant_id == merchant_id)
    if status is not None:
        stmt = stmt.where(PaymentTransaction.status == status)
    if date_from is not None:
        stmt = stmt.where(PaymentTransaction.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(PaymentTransaction.created_at <= date_to)
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_payment_bundle(
    db: Session,
    *,
    transaction_id: str,
) -> tuple[PaymentTransaction, Merchant] | None:
    row = db.execute(
        select(PaymentTransaction, Merchant)
        .join(Merchant, Merchant.id == PaymentTransaction.merchant_db_id)
        .where(PaymentTransaction.transaction_id == transaction_id)
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def list_refunds_for_payment(db: Session, payment_transaction_id: UUID) -> list[RefundTransaction]:
    return list(
        db.scalars(
            select(RefundTransaction)
            .where(RefundTransaction.payment_transaction_id == payment_transaction_id)
            .order_by(RefundTransaction.created_at.desc())
        ).all()
    )


def list_refunds(
    db: Session,
    *,
    refund_transaction_id: str | None = None,
    refund_id: str | None = None,
    merchant_id: str | None = None,
    status=None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> list[tuple[RefundTransaction, Merchant, PaymentTransaction]]:
    stmt = (
        select(RefundTransaction, Merchant, PaymentTransaction)
        .join(Merchant, Merchant.id == RefundTransaction.merchant_db_id)
        .join(PaymentTransaction, PaymentTransaction.id == RefundTransaction.payment_transaction_id)
        .order_by(RefundTransaction.created_at.desc(), RefundTransaction.refund_transaction_id.asc())
        .limit(limit)
    )
    if refund_transaction_id:
        stmt = stmt.where(
            RefundTransaction.refund_transaction_id.like(f"%{refund_transaction_id.strip()}%")
        )
    if refund_id:
        stmt = stmt.where(RefundTransaction.refund_id.like(f"%{refund_id.strip()}%"))
    if merchant_id:
        stmt = stmt.where(Merchant.merchant_id == merchant_id)
    if status is not None:
        stmt = stmt.where(RefundTransaction.status == status)
    if date_from is not None:
        stmt = stmt.where(RefundTransaction.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(RefundTransaction.created_at <= date_to)
    return [(row[0], row[1], row[2]) for row in db.execute(stmt).all()]


def get_refund_bundle(
    db: Session,
    *,
    refund_transaction_id: str,
) -> tuple[RefundTransaction, Merchant, PaymentTransaction] | None:
    row = db.execute(
        select(RefundTransaction, Merchant, PaymentTransaction)
        .join(Merchant, Merchant.id == RefundTransaction.merchant_db_id)
        .join(PaymentTransaction, PaymentTransaction.id == RefundTransaction.payment_transaction_id)
        .where(RefundTransaction.refund_transaction_id == refund_transaction_id)
    ).first()
    if row is None:
        return None
    return row[0], row[1], row[2]


def list_webhooks(
    db: Session,
    *,
    event_type: str | None = None,
    status=None,
    merchant_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> list[tuple[WebhookEvent, Merchant]]:
    stmt = (
        select(WebhookEvent, Merchant)
        .join(Merchant, Merchant.id == WebhookEvent.merchant_db_id)
        .order_by(WebhookEvent.created_at.desc(), WebhookEvent.event_id.asc())
        .limit(limit)
    )
    if event_type:
        stmt = stmt.where(WebhookEvent.event_type == event_type)
    if status is not None:
        stmt = stmt.where(WebhookEvent.status == status)
    if merchant_id:
        stmt = stmt.where(Merchant.merchant_id == merchant_id)
    if date_from is not None:
        stmt = stmt.where(WebhookEvent.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(WebhookEvent.created_at <= date_to)
    return [(row[0], row[1]) for row in db.execute(stmt).all()]


def get_webhook_bundle(
    db: Session,
    *,
    event_id: str,
) -> tuple[WebhookEvent, Merchant] | None:
    row = db.execute(
        select(WebhookEvent, Merchant)
        .join(Merchant, Merchant.id == WebhookEvent.merchant_db_id)
        .where(WebhookEvent.event_id == event_id)
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def list_webhook_attempts(db: Session, webhook_event_id: UUID) -> list[WebhookDeliveryAttempt]:
    return list(
        db.scalars(
            select(WebhookDeliveryAttempt)
            .where(WebhookDeliveryAttempt.webhook_event_id == webhook_event_id)
            .order_by(WebhookDeliveryAttempt.attempt_no.desc())
        ).all()
    )


def list_audit_logs(
    db: Session,
    *,
    actor_type=None,
    actor_id: UUID | None = None,
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 200,
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if actor_type is not None:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if event_type:
        stmt = stmt.where(AuditLog.event_type == event_type)
    if date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    return list(db.scalars(stmt).all())


def list_recent_audit_logs_for_entities(
    db: Session,
    *,
    entity_refs: list[tuple[EntityType, UUID]],
    limit: int = 20,
) -> list[AuditLog]:
    if not entity_refs:
        return []
    clauses = [
        (AuditLog.entity_type == entity_type) & (AuditLog.entity_id == entity_id)
        for entity_type, entity_id in entity_refs
    ]
    return list(
        db.scalars(
            select(AuditLog)
            .where(or_(*clauses))
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        ).all()
    )


def list_callback_logs(
    db: Session,
    *,
    callback_type: CallbackType,
    transaction_reference: str,
    limit: int = 20,
) -> list[BankCallbackLog]:
    return list(
        db.scalars(
            select(BankCallbackLog)
            .where(
                BankCallbackLog.callback_type == callback_type,
                BankCallbackLog.transaction_reference == transaction_reference,
            )
            .order_by(BankCallbackLog.created_at.desc())
            .limit(limit)
        ).all()
    )


def get_latest_reconciliation_for_entity(
    db: Session,
    *,
    entity_type: EntityType,
    entity_id: UUID,
) -> ReconciliationRecord | None:
    return db.scalar(
        select(ReconciliationRecord)
        .where(
            ReconciliationRecord.entity_type == entity_type,
            ReconciliationRecord.entity_id == entity_id,
        )
        .order_by(ReconciliationRecord.created_at.desc())
        .limit(1)
    )


def count_merchants_by_status(db: Session, status: MerchantStatus) -> int:
    return int(db.scalar(select(func.count(Merchant.id)).where(Merchant.status == status)) or 0)


def count_onboarding_cases_by_status(db: Session, status: OnboardingCaseStatus) -> int:
    return int(
        db.scalar(
            select(func.count(MerchantOnboardingCase.id)).where(MerchantOnboardingCase.status == status)
        )
        or 0
    )


def count_payments_created_since(db: Session, since: datetime) -> int:
    return int(
        db.scalar(select(func.count(PaymentTransaction.id)).where(PaymentTransaction.created_at >= since))
        or 0
    )


def sum_successful_payment_amount_since(db: Session, since: datetime) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(PaymentTransaction.amount), 0))
        .where(
            PaymentTransaction.created_at >= since,
            PaymentTransaction.status == PaymentStatus.SUCCESS,
        )
    )
    return Decimal(value or 0)


def count_refunds_created_since(db: Session, since: datetime) -> int:
    return int(
        db.scalar(select(func.count(RefundTransaction.id)).where(RefundTransaction.created_at >= since))
        or 0
    )


def count_webhooks_by_status(db: Session, status) -> int:
    return int(db.scalar(select(func.count(WebhookEvent.id)).where(WebhookEvent.status == status)) or 0)


def count_open_reconciliation_records(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(ReconciliationRecord.id)).where(
                ReconciliationRecord.match_result.in_(
                    [ReconciliationStatus.PENDING_REVIEW, ReconciliationStatus.MISMATCHED]
                )
            )
        )
        or 0
    )


def list_onboarding_queue(db: Session, limit: int = 5) -> list[tuple[Merchant, MerchantOnboardingCase]]:
    return list(
        db.execute(
            select(Merchant, MerchantOnboardingCase)
            .join(MerchantOnboardingCase, MerchantOnboardingCase.merchant_db_id == Merchant.id)
            .where(MerchantOnboardingCase.status == OnboardingCaseStatus.PENDING_REVIEW)
            .order_by(MerchantOnboardingCase.updated_at.desc())
            .limit(limit)
        ).all()
    )


def list_failed_webhook_queue(db: Session, limit: int = 5) -> list[tuple[WebhookEvent, Merchant]]:
    return list(
        db.execute(
            select(WebhookEvent, Merchant)
            .join(Merchant, Merchant.id == WebhookEvent.merchant_db_id)
            .where(WebhookEvent.status == WebhookEventStatus.FAILED)
            .order_by(WebhookEvent.updated_at.desc())
            .limit(limit)
        ).all()
    )


def list_open_reconciliation_queue(db: Session, limit: int = 5) -> list[ReconciliationRecord]:
    return list(
        db.scalars(
            select(ReconciliationRecord)
            .where(
                ReconciliationRecord.match_result.in_(
                    [ReconciliationStatus.PENDING_REVIEW, ReconciliationStatus.MISMATCHED]
                )
            )
            .order_by(ReconciliationRecord.updated_at.desc())
            .limit(limit)
        ).all()
    )


def list_payments_since(db: Session, since: datetime) -> list[PaymentTransaction]:
    return list(
        db.scalars(select(PaymentTransaction).where(PaymentTransaction.created_at >= since)).all()
    )


def aggregate_payment_analytics(
    db: Session,
    *,
    merchant_id: str,
    date_from: datetime,
    date_to: datetime,
):
    bucket_date = func.date(PaymentTransaction.created_at).label("bucket_date")
    successful_amount = func.coalesce(
        func.sum(
            case(
                (PaymentTransaction.status == PaymentStatus.SUCCESS, PaymentTransaction.amount),
                else_=0,
            )
        ),
        0,
    ).label("successful_amount")
    stmt = (
        select(
            bucket_date,
            PaymentTransaction.status.label("status"),
            func.count(PaymentTransaction.id).label("count"),
            successful_amount,
        )
        .join(Merchant, Merchant.id == PaymentTransaction.merchant_db_id)
        .where(
            Merchant.merchant_id == merchant_id,
            PaymentTransaction.created_at >= date_from,
            PaymentTransaction.created_at < date_to,
        )
        .group_by(bucket_date, PaymentTransaction.status)
        .order_by(bucket_date)
    )
    return list(db.execute(stmt).all())


def list_refunds_since(db: Session, since: datetime) -> list[RefundTransaction]:
    return list(
        db.scalars(select(RefundTransaction).where(RefundTransaction.created_at >= since)).all()
    )


def aggregate_refund_analytics(
    db: Session,
    *,
    merchant_id: str,
    date_from: datetime,
    date_to: datetime,
):
    bucket_date = func.date(RefundTransaction.created_at).label("bucket_date")
    refunded_amount = func.coalesce(
        func.sum(
            case(
                (RefundTransaction.status == RefundStatus.REFUNDED, RefundTransaction.refund_amount),
                else_=0,
            )
        ),
        0,
    ).label("amount")
    stmt = (
        select(
            bucket_date,
            RefundTransaction.status.label("status"),
            func.count(RefundTransaction.id).label("count"),
            refunded_amount,
        )
        .join(Merchant, Merchant.id == RefundTransaction.merchant_db_id)
        .where(
            Merchant.merchant_id == merchant_id,
            RefundTransaction.created_at >= date_from,
            RefundTransaction.created_at < date_to,
        )
        .group_by(bucket_date, RefundTransaction.status)
        .order_by(bucket_date)
    )
    return list(db.execute(stmt).all())


def list_webhooks_since(db: Session, since: datetime) -> list[WebhookEvent]:
    return list(db.scalars(select(WebhookEvent).where(WebhookEvent.created_at >= since)).all())


def aggregate_webhook_analytics(
    db: Session,
    *,
    merchant_id: str,
    date_from: datetime,
    date_to: datetime,
):
    bucket_date = func.date(WebhookEvent.created_at).label("bucket_date")
    stmt = (
        select(
            bucket_date,
            WebhookEvent.event_type.label("event_type"),
            WebhookEvent.status.label("status"),
            func.count(WebhookEvent.id).label("count"),
        )
        .join(Merchant, Merchant.id == WebhookEvent.merchant_db_id)
        .where(
            Merchant.merchant_id == merchant_id,
            WebhookEvent.created_at >= date_from,
            WebhookEvent.created_at < date_to,
        )
        .group_by(bucket_date, WebhookEvent.event_type, WebhookEvent.status)
        .order_by(bucket_date)
    )
    return list(db.execute(stmt).all())


def list_reconciliation_records_since(db: Session, since: datetime) -> list[ReconciliationRecord]:
    return list(
        db.scalars(select(ReconciliationRecord).where(ReconciliationRecord.created_at >= since)).all()
    )
