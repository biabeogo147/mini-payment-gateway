from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.time import utc_now
from app.models.enums import CallbackType, EntityType, PaymentStatus, RefundStatus, WebhookEventStatus
from app.models.merchant_user import MerchantUser
from app.repositories import ops_dashboard_repository
from app.schemas.merchant_portal import (
    MerchantPortalAnalyticsAttention,
    MerchantPortalAnalyticsRange,
    MerchantPortalAnalyticsResponse,
    MerchantPortalAnalyticsSeries,
    MerchantPortalAnalyticsTotals,
    MerchantPortalCredentialListResponse,
    MerchantPortalDashboardChartsResponse,
    MerchantPortalDashboardSummaryResponse,
    MerchantPortalPaymentAnalyticsPoint,
    MerchantPortalPaymentAmountChartPoint,
    MerchantPortalProfileResponse,
    MerchantPortalRefundAnalyticsPoint,
    MerchantPortalTopWebhookEventType,
    MerchantPortalWebhookAnalyticsPoint,
)
from app.schemas.ops_dashboard import (
    PaymentDetailResponse,
    PaymentListItemResponse,
    PaymentListResponse,
    PaymentStatusChartPoint,
    RefundCountChartPoint,
    RefundDetailResponse,
    RefundListItemResponse,
    RefundListResponse,
    WebhookEventDetailResponse,
    WebhookEventListItemResponse,
    WebhookEventListResponse,
    WebhookStatusChartPoint,
)


def get_dashboard_summary(
    db: Session,
    *,
    current_user: MerchantUser,
    now: datetime | None = None,
) -> MerchantPortalDashboardSummaryResponse:
    merchant_id = current_user.merchant.merchant_id
    current_time = now or utc_now()
    since = current_time - timedelta(hours=24)
    payments = [item[0] for item in ops_dashboard_repository.list_payments(db, merchant_id=merchant_id, limit=500)]
    refunds = [item[0] for item in ops_dashboard_repository.list_refunds(db, merchant_id=merchant_id, limit=500)]
    webhooks = [item[0] for item in ops_dashboard_repository.list_webhooks(db, merchant_id=merchant_id, limit=500)]

    recent_payments = [payment for payment in payments if _ensure_utc(payment.created_at) >= since]
    recent_refunds = [refund for refund in refunds if _ensure_utc(refund.created_at) >= since]
    successful_amount = sum(
        (payment.amount for payment in recent_payments if payment.status == PaymentStatus.SUCCESS),
        Decimal("0"),
    )

    return MerchantPortalDashboardSummaryResponse(
        payments_last_24h=len(recent_payments),
        successful_payment_amount_last_24h=successful_amount,
        pending_payments=sum(1 for payment in payments if payment.status == PaymentStatus.PENDING),
        refunds_last_24h=len(recent_refunds),
        open_webhook_events=sum(1 for event in webhooks if event.status != WebhookEventStatus.DELIVERED),
    )


def get_dashboard_charts(
    db: Session,
    *,
    current_user: MerchantUser,
    now: datetime | None = None,
) -> MerchantPortalDashboardChartsResponse:
    merchant_id = current_user.merchant.merchant_id
    current_time = _ensure_utc(now or utc_now())
    start_date = current_time.date() - timedelta(days=6)
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)

    payment_buckets = {
        bucket_date: {"pending": 0, "success": 0, "failed": 0, "expired": 0}
        for bucket_date in _date_range(start_date, current_time.date())
    }
    amount_buckets = {bucket_date: Decimal("0") for bucket_date in payment_buckets}
    for payment, _ in ops_dashboard_repository.list_payments(
        db,
        merchant_id=merchant_id,
        date_from=start_dt,
        limit=500,
    ):
        bucket_date = _ensure_utc(payment.created_at).date()
        if bucket_date not in payment_buckets:
            continue
        payment_buckets[bucket_date][payment.status.value.lower()] += 1
        if payment.status == PaymentStatus.SUCCESS:
            amount_buckets[bucket_date] += payment.amount

    refund_buckets = {bucket_date: 0 for bucket_date in payment_buckets}
    for refund, _, _ in ops_dashboard_repository.list_refunds(
        db,
        merchant_id=merchant_id,
        date_from=start_dt,
        limit=500,
    ):
        bucket_date = _ensure_utc(refund.created_at).date()
        if bucket_date in refund_buckets:
            refund_buckets[bucket_date] += 1

    webhook_buckets = {
        bucket_date: {"pending": 0, "delivered": 0, "failed": 0}
        for bucket_date in payment_buckets
    }
    for event, _ in ops_dashboard_repository.list_webhooks(
        db,
        merchant_id=merchant_id,
        date_from=start_dt,
        limit=500,
    ):
        bucket_date = _ensure_utc(event.created_at).date()
        if bucket_date in webhook_buckets:
            webhook_buckets[bucket_date][event.status.value.lower()] += 1

    return MerchantPortalDashboardChartsResponse(
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
        successful_payment_amount_by_day=[
            MerchantPortalPaymentAmountChartPoint(date=bucket_date, amount=amount)
            for bucket_date, amount in amount_buckets.items()
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
    )


def get_analytics(
    db: Session,
    *,
    current_user: MerchantUser,
    days: int = 30,
    now: datetime | None = None,
) -> MerchantPortalAnalyticsResponse:
    if days not in {7, 30, 90}:
        raise AppError(
            error_code="INVALID_ANALYTICS_RANGE",
            message="Analytics range must be one of 7, 30, or 90 days.",
            status_code=422,
            details={"days": days},
        )

    merchant_id = current_user.merchant.merchant_id
    current_time = _ensure_utc(now or utc_now())
    end_date = current_time.date()
    start_date = end_date - timedelta(days=days - 1)
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_exclusive = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)
    dates = _date_range(start_date, end_date)

    payment_buckets = {
        bucket_date: {
            "pending": 0,
            "success": 0,
            "failed": 0,
            "expired": 0,
            "successful_amount": Decimal("0"),
        }
        for bucket_date in dates
    }
    refund_buckets = {
        bucket_date: {
            "pending": 0,
            "refunded": 0,
            "failed": 0,
            "amount": Decimal("0"),
        }
        for bucket_date in dates
    }
    webhook_buckets = {
        bucket_date: {
            "pending": 0,
            "delivered": 0,
            "failed": 0,
        }
        for bucket_date in dates
    }
    webhook_event_type_counts: dict[str, dict[str, int]] = {}

    for row in ops_dashboard_repository.aggregate_payment_analytics(
        db=db,
        merchant_id=merchant_id,
        date_from=start_dt,
        date_to=end_exclusive,
    ):
        bucket_date = _coerce_date(row.bucket_date)
        if bucket_date not in payment_buckets:
            continue
        status = _enum_value(row.status).lower()
        if status in payment_buckets[bucket_date]:
            payment_buckets[bucket_date][status] += int(row.count)
        if status == "success":
            payment_buckets[bucket_date]["successful_amount"] += _coerce_decimal(row.successful_amount)

    for row in ops_dashboard_repository.aggregate_refund_analytics(
        db=db,
        merchant_id=merchant_id,
        date_from=start_dt,
        date_to=end_exclusive,
    ):
        bucket_date = _coerce_date(row.bucket_date)
        if bucket_date not in refund_buckets:
            continue
        status = _enum_value(row.status)
        key = {
            RefundStatus.REFUND_PENDING.value: "pending",
            RefundStatus.REFUNDED.value: "refunded",
            RefundStatus.REFUND_FAILED.value: "failed",
        }.get(status)
        if key is not None:
            refund_buckets[bucket_date][key] += int(row.count)
        if key == "refunded":
            refund_buckets[bucket_date]["amount"] += _coerce_decimal(row.amount)

    for row in ops_dashboard_repository.aggregate_webhook_analytics(
        db=db,
        merchant_id=merchant_id,
        date_from=start_dt,
        date_to=end_exclusive,
    ):
        bucket_date = _coerce_date(row.bucket_date)
        if bucket_date not in webhook_buckets:
            continue
        status = _enum_value(row.status).lower()
        count = int(row.count)
        if status in webhook_buckets[bucket_date]:
            webhook_buckets[bucket_date][status] += count
        if status in {"pending", "failed"}:
            event_type = row.event_type or "unknown"
            event_counts = webhook_event_type_counts.setdefault(event_type, {"pending": 0, "failed": 0})
            event_counts[status] += count

    payment_points: list[MerchantPortalPaymentAnalyticsPoint] = []
    refund_points: list[MerchantPortalRefundAnalyticsPoint] = []
    webhook_points: list[MerchantPortalWebhookAnalyticsPoint] = []

    for bucket_date in dates:
        payment_counts = payment_buckets[bucket_date]
        payment_total = (
            payment_counts["pending"]
            + payment_counts["success"]
            + payment_counts["failed"]
            + payment_counts["expired"]
        )
        payment_points.append(
            MerchantPortalPaymentAnalyticsPoint(
                date=bucket_date,
                pending=payment_counts["pending"],
                success=payment_counts["success"],
                failed=payment_counts["failed"],
                expired=payment_counts["expired"],
                total=payment_total,
                successful_amount=payment_counts["successful_amount"],
                success_rate=_percentage(payment_counts["success"], payment_total),
            )
        )

        refund_counts = refund_buckets[bucket_date]
        refund_count = refund_counts["pending"] + refund_counts["refunded"] + refund_counts["failed"]
        refund_points.append(
            MerchantPortalRefundAnalyticsPoint(
                date=bucket_date,
                pending=refund_counts["pending"],
                refunded=refund_counts["refunded"],
                failed=refund_counts["failed"],
                count=refund_count,
                amount=refund_counts["amount"],
            )
        )

        webhook_counts = webhook_buckets[bucket_date]
        webhook_total = webhook_counts["pending"] + webhook_counts["delivered"] + webhook_counts["failed"]
        webhook_points.append(
            MerchantPortalWebhookAnalyticsPoint(
                date=bucket_date,
                pending=webhook_counts["pending"],
                delivered=webhook_counts["delivered"],
                failed=webhook_counts["failed"],
                total=webhook_total,
                delivery_rate=_percentage(webhook_counts["delivered"], webhook_total),
            )
        )

    payment_count = sum(point.total for point in payment_points)
    successful_payment_count = sum(point.success for point in payment_points)
    refund_count = sum(point.count for point in refund_points)
    webhook_count = sum(point.total for point in webhook_points)
    delivered_webhook_count = sum(point.delivered for point in webhook_points)

    top_webhook_event_types = [
        MerchantPortalTopWebhookEventType(
            event_type=event_type,
            pending=counts["pending"],
            failed=counts["failed"],
            count=counts["pending"] + counts["failed"],
        )
        for event_type, counts in webhook_event_type_counts.items()
    ]
    top_webhook_event_types.sort(key=lambda item: (-item.count, item.event_type))

    return MerchantPortalAnalyticsResponse(
        range=MerchantPortalAnalyticsRange(days=days, start_date=start_date, end_date=end_date),
        totals=MerchantPortalAnalyticsTotals(
            payment_count=payment_count,
            successful_payment_count=successful_payment_count,
            successful_payment_amount=sum((point.successful_amount for point in payment_points), Decimal("0")),
            success_rate=_percentage(successful_payment_count, payment_count),
            refund_count=refund_count,
            refunded_amount=sum((point.amount for point in refund_points), Decimal("0")),
            webhook_count=webhook_count,
            webhook_delivery_rate=_percentage(delivered_webhook_count, webhook_count),
        ),
        series=MerchantPortalAnalyticsSeries(
            payment_by_day=payment_points,
            refund_by_day=refund_points,
            webhook_by_day=webhook_points,
        ),
        attention=MerchantPortalAnalyticsAttention(
            failed_or_expired_payments=sum(point.failed + point.expired for point in payment_points),
            refund_failures=sum(point.failed for point in refund_points),
            open_webhooks=sum(point.pending + point.failed for point in webhook_points),
            top_webhook_event_types=top_webhook_event_types[:5],
        ),
    )


def get_profile(
    db: Session,
    *,
    current_user: MerchantUser,
) -> MerchantPortalProfileResponse:
    return MerchantPortalProfileResponse.from_merchant(current_user.merchant)


def list_credentials(
    db: Session,
    *,
    current_user: MerchantUser,
) -> MerchantPortalCredentialListResponse:
    credentials = ops_dashboard_repository.list_credentials_for_merchant(db, current_user.merchant_db_id)
    return MerchantPortalCredentialListResponse.from_credentials(credentials)


def list_payments(
    db: Session,
    *,
    current_user: MerchantUser,
    transaction_id: str | None = None,
    order_id: str | None = None,
    status=None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> PaymentListResponse:
    rows = ops_dashboard_repository.list_payments(
        db,
        transaction_id=transaction_id,
        order_id=order_id,
        merchant_id=current_user.merchant.merchant_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return PaymentListResponse(
        payments=[PaymentListItemResponse.from_payment(payment, merchant) for payment, merchant in rows]
    )


def get_payment_detail(
    db: Session,
    *,
    current_user: MerchantUser,
    transaction_id: str,
) -> PaymentDetailResponse:
    payment, merchant = _require_payment_bundle(db, current_user=current_user, transaction_id=transaction_id)
    callback_logs = ops_dashboard_repository.list_callback_logs(
        db,
        callback_type=CallbackType.PAYMENT_RESULT,
        transaction_reference=payment.transaction_id,
        limit=10,
    )
    refunds = ops_dashboard_repository.list_refunds_for_payment(db, payment.id)
    return PaymentDetailResponse.from_bundle(
        payment=payment,
        merchant=merchant,
        callback_logs=callback_logs,
        refunds=refunds,
        reconciliation=None,
    )


def list_refunds(
    db: Session,
    *,
    current_user: MerchantUser,
    refund_transaction_id: str | None = None,
    refund_id: str | None = None,
    status=None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> RefundListResponse:
    rows = ops_dashboard_repository.list_refunds(
        db,
        refund_transaction_id=refund_transaction_id,
        refund_id=refund_id,
        merchant_id=current_user.merchant.merchant_id,
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


def get_refund_detail(
    db: Session,
    *,
    current_user: MerchantUser,
    refund_transaction_id: str,
) -> RefundDetailResponse:
    bundle = ops_dashboard_repository.get_refund_bundle(db, refund_transaction_id=refund_transaction_id)
    if bundle is None or bundle[0].merchant_db_id != current_user.merchant_db_id:
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
    return RefundDetailResponse.from_full_bundle(
        refund=refund,
        merchant=merchant,
        payment=payment,
        callback_logs=callback_logs,
        reconciliation=None,
    )


def list_webhooks(
    db: Session,
    *,
    current_user: MerchantUser,
    event_type: str | None = None,
    status=None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 100,
) -> WebhookEventListResponse:
    rows = ops_dashboard_repository.list_webhooks(
        db,
        event_type=event_type,
        status=status,
        merchant_id=current_user.merchant.merchant_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return WebhookEventListResponse(
        events=[
            WebhookEventListItemResponse.from_bundle(event=event, merchant=merchant)
            for event, merchant in rows
        ]
    )


def get_webhook_detail(
    db: Session,
    *,
    current_user: MerchantUser,
    event_id: str,
) -> WebhookEventDetailResponse:
    bundle = ops_dashboard_repository.get_webhook_bundle(db, event_id=event_id)
    if bundle is None or bundle[0].merchant_db_id != current_user.merchant_db_id:
        raise AppError(
            error_code="WEBHOOK_EVENT_NOT_FOUND",
            message="Webhook event not found.",
            status_code=404,
            details={"event_id": event_id},
        )
    event, merchant = bundle
    attempts = ops_dashboard_repository.list_webhook_attempts(db, event.id)
    return WebhookEventDetailResponse.from_full_bundle(
        event=event,
        merchant=merchant,
        attempts=attempts,
    )


def _require_payment_bundle(
    db: Session,
    *,
    current_user: MerchantUser,
    transaction_id: str,
):
    bundle = ops_dashboard_repository.get_payment_bundle(db, transaction_id=transaction_id)
    if bundle is None or bundle[0].merchant_db_id != current_user.merchant_db_id:
        raise AppError(
            error_code="PAYMENT_NOT_FOUND",
            message="Payment not found.",
            status_code=404,
            details={"transaction_id": transaction_id},
        )
    return bundle


def _date_range(start_date: date, end_date: date) -> list[date]:
    days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=offset) for offset in range(days)]


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_date(value) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value.date()


def _coerce_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _enum_value(value) -> str:
    return getattr(value, "value", str(value))


def _percentage(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)
