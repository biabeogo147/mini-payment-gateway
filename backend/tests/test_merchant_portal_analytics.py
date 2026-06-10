import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.enums import PaymentStatus, RefundStatus, WebhookEventStatus
from tests.merchant_portal_test_utils import make_merchant_user, override_current_merchant_user


class MerchantPortalAnalyticsRouteTest(unittest.TestCase):
    def test_analytics_route_defaults_to_30_days_and_passes_current_user(self) -> None:
        from app.controllers import merchant_portal_controller
        from app.core.errors import AppError
        from app.main import app

        db = object()
        merchant_user = make_merchant_user()
        self._override_db(app, db)
        override_current_merchant_user(app, merchant_user)

        def analytics_response(**kwargs):
            days = kwargs["days"]
            if days not in {7, 30, 90}:
                raise AppError(
                    "INVALID_ANALYTICS_RANGE",
                    "Analytics range must be 7, 30, or 90 days.",
                    status_code=422,
                )
            return {
                "range": {
                    "days": days,
                    "start_date": "2026-05-12",
                    "end_date": "2026-06-10",
                },
                "totals": {
                    "payment_count": 1,
                    "successful_payment_count": 1,
                    "successful_payment_amount": "125000.00",
                    "success_rate": 100.0,
                    "refund_count": 0,
                    "refunded_amount": "0",
                    "webhook_count": 0,
                    "webhook_delivery_rate": 0.0,
                },
                "series": {
                    "payment_by_day": [],
                    "refund_by_day": [],
                    "webhook_by_day": [],
                },
                "attention": {
                    "failed_or_expired_payments": 0,
                    "refund_failures": 0,
                    "open_webhooks": 0,
                    "top_webhook_event_types": [],
                },
            }

        try:
            with patch.object(
                merchant_portal_controller.merchant_portal_service,
                "get_analytics",
                side_effect=analytics_response,
            ) as analytics_service:
                response = TestClient(app).get("/v1/merchant-portal/analytics")
                seven_day_response = TestClient(app).get(
                    "/v1/merchant-portal/analytics",
                    params={"days": "7"},
                )
                invalid_response = TestClient(app).get("/v1/merchant-portal/analytics", params={"days": "14"})
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["range"]["days"], 30)
        self.assertEqual(seven_day_response.status_code, 200)
        self.assertEqual(invalid_response.status_code, 422)
        self.assertIs(analytics_service.call_args_list[0].kwargs["db"], db)
        self.assertIs(analytics_service.call_args_list[0].kwargs["current_user"], merchant_user)
        self.assertEqual(analytics_service.call_args_list[0].kwargs["days"], 30)
        self.assertEqual(analytics_service.call_args_list[1].kwargs["days"], 7)

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


class MerchantPortalAnalyticsServiceTest(unittest.TestCase):
    def test_service_builds_zero_filled_scoped_series_totals_and_attention(self) -> None:
        from app.services import merchant_portal_service

        merchant_user = make_merchant_user()
        merchant_user.merchant.merchant_id = "m_alpha"
        db = object()
        now = datetime(2026, 6, 10, 12, 0, tzinfo=timezone.utc)

        with patch.object(
            merchant_portal_service.ops_dashboard_repository,
            "aggregate_payment_analytics",
            return_value=[
                _payment_row(date(2026, 6, 8), PaymentStatus.SUCCESS, 2, "100000.00"),
                _payment_row(date(2026, 6, 9), PaymentStatus.FAILED, 1, "0"),
                _payment_row(date(2026, 6, 10), PaymentStatus.EXPIRED, 1, "0"),
            ],
        ) as payment_repo, patch.object(
            merchant_portal_service.ops_dashboard_repository,
            "aggregate_refund_analytics",
            return_value=[
                _refund_row(date(2026, 6, 9), RefundStatus.REFUNDED, 1, "25000.00"),
                _refund_row(date(2026, 6, 10), RefundStatus.REFUND_FAILED, 1, "0"),
            ],
        ) as refund_repo, patch.object(
            merchant_portal_service.ops_dashboard_repository,
            "aggregate_webhook_analytics",
            return_value=[
                _webhook_row(date(2026, 6, 9), "payment.succeeded", WebhookEventStatus.DELIVERED, 3),
                _webhook_row(date(2026, 6, 10), "payment.expired", WebhookEventStatus.PENDING, 2),
                _webhook_row(date(2026, 6, 10), "refund.refunded", WebhookEventStatus.FAILED, 1),
            ],
        ) as webhook_repo:
            response = merchant_portal_service.get_analytics(
                db=db,
                current_user=merchant_user,
                days=7,
                now=now,
            )

        self.assertEqual(response.range.days, 7)
        self.assertEqual(response.range.start_date, date(2026, 6, 4))
        self.assertEqual(response.range.end_date, date(2026, 6, 10))
        self.assertEqual([point.date for point in response.series.payment_by_day][0], date(2026, 6, 4))
        self.assertEqual([point.date for point in response.series.payment_by_day][-1], date(2026, 6, 10))

        june_8 = response.series.payment_by_day[4]
        june_9 = response.series.payment_by_day[5]
        june_10_payment = response.series.payment_by_day[6]
        self.assertEqual(june_8.success, 2)
        self.assertEqual(june_8.successful_amount, Decimal("100000.00"))
        self.assertEqual(june_8.success_rate, 100.0)
        self.assertEqual(june_9.failed, 1)
        self.assertEqual(june_10_payment.expired, 1)

        june_10_refund = response.series.refund_by_day[6]
        self.assertEqual(june_10_refund.failed, 1)
        self.assertEqual(june_10_refund.amount, Decimal("0"))

        june_10_webhook = response.series.webhook_by_day[6]
        self.assertEqual(june_10_webhook.pending, 2)
        self.assertEqual(june_10_webhook.failed, 1)
        self.assertEqual(june_10_webhook.delivery_rate, 0.0)

        self.assertEqual(response.totals.payment_count, 4)
        self.assertEqual(response.totals.successful_payment_count, 2)
        self.assertEqual(response.totals.successful_payment_amount, Decimal("100000.00"))
        self.assertEqual(response.totals.success_rate, 50.0)
        self.assertEqual(response.totals.refund_count, 2)
        self.assertEqual(response.totals.refunded_amount, Decimal("25000.00"))
        self.assertEqual(response.totals.webhook_count, 6)
        self.assertEqual(response.totals.webhook_delivery_rate, 50.0)
        self.assertEqual(response.attention.failed_or_expired_payments, 2)
        self.assertEqual(response.attention.refund_failures, 1)
        self.assertEqual(response.attention.open_webhooks, 3)
        self.assertEqual(response.attention.top_webhook_event_types[0].event_type, "payment.expired")

        for repo in [payment_repo, refund_repo, webhook_repo]:
            self.assertIs(repo.call_args.kwargs["db"], db)
            self.assertEqual(repo.call_args.kwargs["merchant_id"], "m_alpha")


def _payment_row(bucket_date: date, status: PaymentStatus, count: int, amount: str):
    return SimpleNamespace(
        bucket_date=bucket_date,
        status=status,
        count=count,
        successful_amount=Decimal(amount),
    )


def _refund_row(bucket_date: date, status: RefundStatus, count: int, amount: str):
    return SimpleNamespace(
        bucket_date=bucket_date,
        status=status,
        count=count,
        amount=Decimal(amount),
    )


def _webhook_row(bucket_date: date, event_type: str, status: WebhookEventStatus, count: int):
    return SimpleNamespace(
        bucket_date=bucket_date,
        event_type=event_type,
        status=status,
        count=count,
    )


if __name__ == "__main__":
    unittest.main()
