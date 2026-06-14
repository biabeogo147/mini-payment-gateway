import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import EntityType, PaymentStatus, RefundStatus, WebhookEventStatus
from app.schemas.merchant_portal import (
    MerchantPortalDashboardChartsResponse,
    MerchantPortalDashboardSummaryResponse,
    MerchantPortalPaymentAmountChartPoint,
    MerchantPortalProfileResponse,
    MerchantPortalCredentialListResponse,
)
from app.schemas.ops_dashboard import (
    MerchantCredentialDetailResponse,
    PaymentListItemResponse,
    PaymentListResponse,
    PaymentStatusChartPoint,
    RefundCountChartPoint,
    RefundListItemResponse,
    RefundListResponse,
    WebhookEventListItemResponse,
    WebhookEventListResponse,
    WebhookStatusChartPoint,
)
from tests.merchant_portal_test_utils import make_merchant_user, override_current_merchant_user


class MerchantPortalRouteTest(unittest.TestCase):
    def test_summary_charts_profile_and_credentials_routes_use_current_merchant_user(self) -> None:
        from app.controllers import merchant_portal_controller
        from app.main import app

        db = object()
        merchant_user = make_merchant_user()
        self._override_db(app, db)
        override_current_merchant_user(app, merchant_user)

        try:
            with patch.object(
                merchant_portal_controller.merchant_portal_service,
                "get_dashboard_summary",
                return_value=MerchantPortalDashboardSummaryResponse(
                    payments_last_24h=3,
                    successful_payment_amount_last_24h=Decimal("120000.00"),
                    pending_payments=1,
                    refunds_last_24h=1,
                    open_webhook_events=2,
                ),
            ) as summary_service, patch.object(
                merchant_portal_controller.merchant_portal_service,
                "get_dashboard_charts",
                return_value=MerchantPortalDashboardChartsResponse(
                    payment_status_by_day=[
                        PaymentStatusChartPoint(date=date(2026, 6, 9), pending=1, success=2, failed=0, expired=0)
                    ],
                    successful_payment_amount_by_day=[
                        MerchantPortalPaymentAmountChartPoint(date=date(2026, 6, 9), amount=Decimal("120000.00"))
                    ],
                    refund_count_by_day=[RefundCountChartPoint(date=date(2026, 6, 9), count=1)],
                    webhook_status_by_day=[
                        WebhookStatusChartPoint(date=date(2026, 6, 9), pending=1, delivered=1, failed=1)
                    ],
                ),
            ) as charts_service, patch.object(
                merchant_portal_controller.merchant_portal_service,
                "get_profile",
                return_value=MerchantPortalProfileResponse(
                    merchant_id="m_demo",
                    merchant_name="Demo Merchant",
                    legal_name=None,
                    contact_name=None,
                    contact_email="m_demo@example.com",
                    contact_phone=None,
                    webhook_url="https://merchant.example.com/webhook",
                    allowed_ip_list=None,
                    status="ACTIVE",
                    created_at=datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc),
                    updated_at=datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc),
                ),
            ) as profile_service, patch.object(
                merchant_portal_controller.merchant_portal_service,
                "list_credentials",
                return_value=MerchantPortalCredentialListResponse(credentials=[]),
            ) as credential_service:
                summary_response = TestClient(app).get("/v1/merchant-portal/dashboard/summary")
                charts_response = TestClient(app).get("/v1/merchant-portal/dashboard/charts")
                profile_response = TestClient(app).get("/v1/merchant-portal/profile")
                credential_response = TestClient(app).get("/v1/merchant-portal/credentials")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(charts_response.status_code, 200)
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(credential_response.status_code, 200)
        for service in [summary_service, charts_service, profile_service, credential_service]:
            self.assertIs(service.call_args.kwargs["db"], db)
            self.assertIs(service.call_args.kwargs["current_user"], merchant_user)

    def test_payment_refund_and_webhook_routes_pass_filters_and_current_merchant_user(self) -> None:
        from app.controllers import merchant_portal_controller
        from app.main import app

        db = object()
        merchant_user = make_merchant_user()
        self._override_db(app, db)
        override_current_merchant_user(app, merchant_user)
        entity_id = uuid4()

        try:
            with patch.object(
                merchant_portal_controller.merchant_portal_service,
                "list_payments",
                return_value=PaymentListResponse(
                    payments=[
                        PaymentListItemResponse(
                            transaction_id="pay_demo",
                            merchant_id="m_demo",
                            merchant_name="Demo Merchant",
                            order_id="ORDER-1",
                            amount=Decimal("100000.00"),
                            currency="VND",
                            status=PaymentStatus.SUCCESS,
                            expire_at=datetime(2026, 6, 9, 10, 30, tzinfo=timezone.utc),
                            paid_at=datetime(2026, 6, 9, 10, 5, tzinfo=timezone.utc),
                            created_at=datetime(2026, 6, 9, 10, 0, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as payment_service, patch.object(
                merchant_portal_controller.merchant_portal_service,
                "list_refunds",
                return_value=RefundListResponse(
                    refunds=[
                        RefundListItemResponse(
                            refund_transaction_id="rfnd_demo",
                            refund_id="REF-1",
                            merchant_id="m_demo",
                            merchant_name="Demo Merchant",
                            original_transaction_id="pay_demo",
                            refund_amount=Decimal("100000.00"),
                            refund_status=RefundStatus.REFUNDED,
                            reason="Customer request",
                            created_at=datetime(2026, 6, 9, 11, 0, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as refund_service, patch.object(
                merchant_portal_controller.merchant_portal_service,
                "list_webhooks",
                return_value=WebhookEventListResponse(
                    events=[
                        WebhookEventListItemResponse(
                            event_id="evt_demo",
                            merchant_id="m_demo",
                            merchant_name="Demo Merchant",
                            event_type="PAYMENT_COMPLETED",
                            entity_type=EntityType.PAYMENT,
                            entity_id=str(entity_id),
                            status=WebhookEventStatus.DELIVERED,
                            attempt_count=1,
                            next_retry_at=None,
                            last_attempt_at=datetime(2026, 6, 9, 10, 6, tzinfo=timezone.utc),
                            created_at=datetime(2026, 6, 9, 10, 5, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as webhook_service:
                payment_response = TestClient(app).get(
                    "/v1/merchant-portal/payments",
                    params={"order_id": "ORDER-1", "status": "SUCCESS", "limit": "10"},
                )
                refund_response = TestClient(app).get(
                    "/v1/merchant-portal/refunds",
                    params={"refund_id": "REF-1", "status": "REFUNDED", "limit": "10"},
                )
                webhook_response = TestClient(app).get(
                    "/v1/merchant-portal/webhooks",
                    params={"event_type": "PAYMENT_COMPLETED", "status": "DELIVERED", "limit": "10"},
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(payment_response.status_code, 200)
        self.assertEqual(refund_response.status_code, 200)
        self.assertEqual(webhook_response.status_code, 200)
        self.assertIs(payment_service.call_args.kwargs["current_user"], merchant_user)
        self.assertEqual(payment_service.call_args.kwargs["order_id"], "ORDER-1")
        self.assertNotIn("merchant_id", payment_service.call_args.kwargs)
        self.assertEqual(refund_service.call_args.kwargs["refund_id"], "REF-1")
        self.assertEqual(webhook_service.call_args.kwargs["event_type"], "PAYMENT_COMPLETED")

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
