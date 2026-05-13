from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utc_now
from app.models.enums import (
    CallbackType,
    EntityType,
    MerchantStatus,
    ReconciliationStatus,
    WebhookEventStatus,
)
from app.repositories import ops_dashboard_repository
from app.schemas.ops_dashboard import (
    AuditLogItemResponse,
    AuditLogListResponse,
    DashboardChartsResponse,
    DashboardMerchantQueueItemResponse,
    DashboardReconciliationQueueItemResponse,
    DashboardSummaryResponse,
    DashboardWebhookQueueItemResponse,
    MerchantCredentialDetailResponse,
    MerchantCredentialListResponse,
    MerchantDetailResponse,
    MerchantListItemResponse,
    MerchantListResponse,
    OnboardingCaseDetailResponse,
    PaymentDetailResponse,
    PaymentListItemResponse,
    PaymentListResponse,
    PaymentStatusChartPoint,
    ReconciliationChartPoint,
    RefundCountChartPoint,
    RefundDetailResponse,
    RefundListItemResponse,
    RefundListResponse,
    WebhookAttemptsListResponse,
    WebhookAttemptResponse,
    WebhookEventDetailResponse,
    WebhookEventListItemResponse,
    WebhookEventListResponse,
    WebhookStatusChartPoint,
)


def list_merchants(
    db: Session,
    *,
    search: str | None = None,
    status=None,
    onboarding_status=None,
    limit: int = 100,
) -> MerchantListResponse:
    rows = ops_dashboard_repository.list_merchants(
        db,
        search=search,
        status=status,
        onboarding_status=onboarding_status,
        limit=limit,
    )
    return MerchantListResponse(
        merchants=[
            MerchantListItemResponse.from_bundle(merchant=merchant, onboarding_case=onboarding_case)
            for merchant, onboarding_case in rows
        ]
    )


def get_merchant_detail(db: Session, *, merchant_id: str) -> MerchantDetailResponse:
    bundle = ops_dashboard_repository.get_merchant_bundle(db, merchant_id=merchant_id)
    if bundle is None:
        raise AppError(
            error_code="MERCHANT_NOT_FOUND",
            message="Merchant not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    merchant, onboarding_case = bundle
    credentials = ops_dashboard_repository.list_credentials_for_merchant(db, merchant.id)
    recent_payments = ops_dashboard_repository.list_payments(db, merchant_id=merchant_id, limit=5)
    recent_refunds = ops_dashboard_repository.list_refunds(db, merchant_id=merchant_id, limit=5)
    recent_webhooks = ops_dashboard_repository.list_webhooks(db, merchant_id=merchant_id, limit=5)
    entity_refs = [(EntityType.MERCHANT, merchant.id)]
    if onboarding_case is not None:
        entity_refs.append((EntityType.ONBOARDING_CASE, onboarding_case.id))
    entity_refs.extend((EntityType.MERCHANT_CREDENTIAL, credential.id) for credential in credentials)
    recent_audit_logs = ops_dashboard_repository.list_recent_audit_logs_for_entities(
        db,
        entity_refs=entity_refs,
        limit=10,
    )
    return MerchantDetailResponse.from_full_bundle(
        merchant=merchant,
        onboarding_case=onboarding_case,
        credentials=credentials,
        recent_payments=recent_payments,
        recent_refunds=recent_refunds,
        recent_webhooks=recent_webhooks,
        recent_audit_logs=recent_audit_logs,
    )


def get_merchant_onboarding_case(db: Session, *, merchant_id: str) -> OnboardingCaseDetailResponse:
    bundle = ops_dashboard_repository.get_merchant_bundle(db, merchant_id=merchant_id)
    if bundle is None:
        raise AppError(
            error_code="MERCHANT_NOT_FOUND",
            message="Merchant not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    _, onboarding_case = bundle
    if onboarding_case is None:
        raise AppError(
            error_code="ONBOARDING_CASE_NOT_FOUND",
            message="Onboarding case not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    return OnboardingCaseDetailResponse.from_case(onboarding_case)


def list_merchant_credentials(db: Session, *, merchant_id: str) -> MerchantCredentialListResponse:
    bundle = ops_dashboard_repository.get_merchant_bundle(db, merchant_id=merchant_id)
    if bundle is None:
        raise AppError(
            error_code="MERCHANT_NOT_FOUND",
            message="Merchant not found.",
            status_code=404,
            details={"merchant_id": merchant_id},
        )
    merchant, _ = bundle
    credentials = ops_dashboard_repository.list_credentials_for_merchant(db, merchant.id)
    return MerchantCredentialListResponse(
        credentials=[MerchantCredentialDetailResponse.from_credential(item) for item in credentials]
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
) -> PaymentListResponse:
    rows = ops_dashboard_repository.list_payments(
        db,
        transaction_id=transaction_id,
        order_id=order_id,
        merchant_id=merchant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return PaymentListResponse(
        payments=[PaymentListItemResponse.from_payment(payment, merchant) for payment, merchant in rows]
    )


def get_payment_detail(db: Session, *, transaction_id: str) -> PaymentDetailResponse:
    bundle = ops_dashboard_repository.get_payment_bundle(db, transaction_id=transaction_id)
    if bundle is None:
        raise AppError(
            error_code="PAYMENT_NOT_FOUND",
            message="Payment not found.",
            status_code=404,
            details={"transaction_id": transaction_id},
        )
    payment, merchant = bundle
    callback_logs = ops_dashboard_repository.list_callback_logs(
        db,
        callback_type=CallbackType.PAYMENT_RESULT,
        transaction_reference=payment.transaction_id,
        limit=10,
    )
    refunds = ops_dashboard_repository.list_refunds_for_payment(db, payment.id)
    reconciliation = ops_dashboard_repository.get_latest_reconciliation_for_entity(
        db,
        entity_type=EntityType.PAYMENT,
        entity_id=payment.id,
    )
    return PaymentDetailResponse.from_bundle(
        payment=payment,
        merchant=merchant,
        callback_logs=callback_logs,
        refunds=refunds,
        reconciliation=reconciliation,
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
) -> RefundListResponse:
    rows = ops_dashboard_repository.list_refunds(
        db,
        refund_transaction_id=refund_transaction_id,
        refund_id=refund_id,
        merchant_id=merchant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return RefundListResponse(
        refunds=[
            RefundListItemResponse.from_bundle(refund=refund, merchant=merchant, payment=payment)
            for refund, merchant, payment in rows
        ]
    )


def get_refund_detail(db: Session, *, refund_transaction_id: str) -> RefundDetailResponse:
    bundle = ops_dashboard_repository.get_refund_bundle(db, refund_transaction_id=refund_transaction_id)
    if bundle is None:
        raise AppError(
            error_code="REFUND_NOT_FOUND",
            message="Refund not found.",
            status_code=404,
            details={"refund_transaction_id": refund_transaction_id},
        )
    refund, merchant, payment = bundle
    callback_logs = ops_dashboard_repository.list_callback_logs(
        db,
        callback_type=CallbackType.REFUND_RESULT,
        transaction_reference=refund.refund_transaction_id,
        limit=10,
    )
    reconciliation = ops_dashboard_repository.get_latest_reconciliation_for_entity(
        db,
        entity_type=EntityType.REFUND,
        entity_id=refund.id,
    )
    return RefundDetailResponse.from_full_bundle(
        refund=refund,
        merchant=merchant,
        payment=payment,
        callback_logs=callback_logs,
        reconciliation=reconciliation,
    )


def list_webhooks(
    db: Session,
    *,
    event_type: str | None = None,
    status=None,
    merchant_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> WebhookEventListResponse:
    rows = ops_dashboard_repository.list_webhooks(
        db,
        event_type=event_type,
        status=status,
        merchant_id=merchant_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return WebhookEventListResponse(
        events=[WebhookEventListItemResponse.from_bundle(event=event, merchant=merchant) for event, merchant in rows]
    )


def get_webhook_detail(db: Session, *, event_id: str) -> WebhookEventDetailResponse:
    bundle = ops_dashboard_repository.get_webhook_bundle(db, event_id=event_id)
    if bundle is None:
        raise AppError(
            error_code="WEBHOOK_EVENT_NOT_FOUND",
            message="Webhook event not found.",
            status_code=404,
            details={"event_id": event_id},
        )
    event, merchant = bundle
    attempts = ops_dashboard_repository.list_webhook_attempts(db, event.id)
    return WebhookEventDetailResponse.from_full_bundle(event=event, merchant=merchant, attempts=attempts)


def list_webhook_attempts(db: Session, *, event_id: str) -> WebhookAttemptsListResponse:
    bundle = ops_dashboard_repository.get_webhook_bundle(db, event_id=event_id)
    if bundle is None:
        raise AppError(
            error_code="WEBHOOK_EVENT_NOT_FOUND",
            message="Webhook event not found.",
            status_code=404,
            details={"event_id": event_id},
        )
    event, _ = bundle
    return WebhookAttemptsListResponse(
        attempts=[
            WebhookAttemptResponse.from_attempt(item)
            for item in ops_dashboard_repository.list_webhook_attempts(db, event.id)
        ]
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
) -> AuditLogListResponse:
    logs = ops_dashboard_repository.list_audit_logs(
        db,
        actor_type=actor_type,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return AuditLogListResponse(logs=[AuditLogItemResponse.from_log(item) for item in logs])


def get_dashboard_summary(
    db: Session,
    *,
    now: datetime | None = None,
) -> DashboardSummaryResponse:
    current_time = now or utc_now()
    since = current_time - timedelta(hours=24)
    onboarding_queue = ops_dashboard_repository.list_onboarding_queue(db, limit=5)
    failed_webhooks = ops_dashboard_repository.list_failed_webhook_queue(db, limit=5)
    reconciliation_queue = ops_dashboard_repository.list_open_reconciliation_queue(db, limit=5)

    return DashboardSummaryResponse(
        merchants_pending_review=ops_dashboard_repository.count_merchants_by_status(
            db,
            status=MerchantStatus.PENDING_REVIEW,
        ),
        merchants_active=ops_dashboard_repository.count_merchants_by_status(
            db,
            status=MerchantStatus.ACTIVE,
        ),
        payments_last_24h=ops_dashboard_repository.count_payments_created_since(db, since),
        successful_payment_amount_last_24h=ops_dashboard_repository.sum_successful_payment_amount_since(db, since),
        refunds_last_24h=ops_dashboard_repository.count_refunds_created_since(db, since),
        failed_webhook_events_open=ops_dashboard_repository.count_webhooks_by_status(
            db,
            status=WebhookEventStatus.FAILED,
        ),
        reconciliation_open=ops_dashboard_repository.count_open_reconciliation_records(db),
        onboarding_queue=[
            DashboardMerchantQueueItemResponse.from_bundle(merchant=merchant, onboarding_case=onboarding_case)
            for merchant, onboarding_case in onboarding_queue
        ],
        failed_webhooks=[
            DashboardWebhookQueueItemResponse.from_bundle(event=event, merchant=merchant)
            for event, merchant in failed_webhooks
        ],
        reconciliation_queue=[
            DashboardReconciliationQueueItemResponse.from_record(record)
            for record in reconciliation_queue
        ],
    )


def get_dashboard_charts(
    db: Session,
    *,
    now: datetime | None = None,
) -> DashboardChartsResponse:
    current_time = _ensure_utc(now or utc_now())
    start_date = current_time.date() - timedelta(days=6)
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)

    payment_buckets = {
        bucket_date: {"pending": 0, "success": 0, "failed": 0, "expired": 0}
        for bucket_date in _date_range(start_date, current_time.date())
    }
    for payment in ops_dashboard_repository.list_payments_since(db, start_dt):
        bucket = payment_buckets.get(_ensure_utc(payment.created_at).date())
        if bucket is not None:
            bucket[payment.status.value.lower()] += 1

    refund_buckets = {bucket_date: 0 for bucket_date in _date_range(start_date, current_time.date())}
    for refund in ops_dashboard_repository.list_refunds_since(db, start_dt):
        refund_date = _ensure_utc(refund.created_at).date()
        if refund_date in refund_buckets:
            refund_buckets[refund_date] += 1

    webhook_buckets = {
        bucket_date: {"pending": 0, "delivered": 0, "failed": 0}
        for bucket_date in _date_range(start_date, current_time.date())
    }
    for event in ops_dashboard_repository.list_webhooks_since(db, start_dt):
        event_date = _ensure_utc(event.created_at).date()
        bucket = webhook_buckets.get(event_date)
        if bucket is not None:
            bucket[event.status.value.lower()] += 1

    reconciliation_created = {bucket_date: 0 for bucket_date in _date_range(start_date, current_time.date())}
    for record in ops_dashboard_repository.list_reconciliation_records_since(db, start_dt):
        record_date = _ensure_utc(record.created_at).date()
        if record_date in reconciliation_created:
            reconciliation_created[record_date] += 1

    reconciliation_resolved = defaultdict(int)
    resolved_logs = ops_dashboard_repository.list_audit_logs(
        db,
        entity_type=EntityType.RECONCILIATION,
        event_type="RECONCILIATION_RESOLVED",
        date_from=start_dt,
        limit=500,
    )
    for log in resolved_logs:
        reconciliation_resolved[_ensure_utc(log.created_at).date()] += 1

    return DashboardChartsResponse(
        payment_status_by_day=[
            PaymentStatusChartPoint(
                date=bucket_date,
                pending=counts["pending"],
                success=counts["success"],
                failed=counts["failed"],
                expired=counts["expired"],
            )
            for bucket_date, counts in payment_buckets.items()
        ],
        refund_count_by_day=[
            RefundCountChartPoint(date=bucket_date, count=count)
            for bucket_date, count in refund_buckets.items()
        ],
        webhook_status_by_day=[
            WebhookStatusChartPoint(
                date=bucket_date,
                pending=counts["pending"],
                delivered=counts["delivered"],
                failed=counts["failed"],
            )
            for bucket_date, counts in webhook_buckets.items()
        ],
        reconciliation_by_day=[
            ReconciliationChartPoint(
                date=bucket_date,
                created=reconciliation_created[bucket_date],
                resolved=reconciliation_resolved[bucket_date],
            )
            for bucket_date in reconciliation_created
        ],
    )


def _date_range(start_date: date, end_date: date) -> list[date]:
    days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(days)]


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
