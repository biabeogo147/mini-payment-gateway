import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import ActorType, EntityType, MerchantStatus, OnboardingCaseStatus, PaymentStatus, WebhookEventStatus
from app.schemas.ops_dashboard import (
    AuditLogItemResponse,
    AuditLogListResponse,
    DashboardChartsResponse,
    DashboardSummaryResponse,
    MerchantListItemResponse,
    MerchantListResponse,
    PaymentListItemResponse,
    PaymentListResponse,
    PaymentStatusChartPoint,
    ReconciliationChartPoint,
    RefundCountChartPoint,
    WebhookEventListItemResponse,
    WebhookEventListResponse,
    WebhookStatusChartPoint,
)
from tests.internal_auth_test_utils import make_internal_user, override_current_internal_user


class OpsDashboardRouteTest(unittest.TestCase):
    def test_summary_and_chart_routes_call_service(self) -> None:
        from app.controllers import ops_dashboard_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())
        now = datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc)

        try:
            with patch.object(
                ops_dashboard_controller.ops_dashboard_service,
                "get_dashboard_summary",
                return_value=DashboardSummaryResponse(
                    merchants_pending_review=2,
                    merchants_active=5,
                    payments_last_24h=10,
                    successful_payment_amount_last_24h=Decimal("1250000.00"),
                    refunds_last_24h=1,
                    failed_webhook_events_open=3,
                    reconciliation_open=2,
                    onboarding_queue=[],
                    failed_webhooks=[],
                    reconciliation_queue=[],
                ),
            ) as summary_service, patch.object(
                ops_dashboard_controller.ops_dashboard_service,
                "get_dashboard_charts",
                return_value=DashboardChartsResponse(
                    payment_status_by_day=[
                        PaymentStatusChartPoint(date=date(2026, 5, 13), pending=1, success=2, failed=0, expired=0)
                    ],
                    refund_count_by_day=[RefundCountChartPoint(date=date(2026, 5, 13), count=1)],
                    webhook_status_by_day=[
                        WebhookStatusChartPoint(date=date(2026, 5, 13), pending=1, delivered=1, failed=1)
                    ],
                    reconciliation_by_day=[
                        ReconciliationChartPoint(date=date(2026, 5, 13), created=2, resolved=1)
                    ],
                ),
            ) as chart_service:
                summary_response = TestClient(app).get("/v1/ops/dashboard/summary")
                chart_response = TestClient(app).get("/v1/ops/dashboard/charts")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(chart_response.status_code, 200)
        self.assertEqual(summary_response.json()["merchants_active"], 5)
        self.assertEqual(chart_response.json()["payment_status_by_day"][0]["success"], 2)
        self.assertIs(summary_service.call_args.kwargs["db"], db)
        self.assertIs(chart_service.call_args.kwargs["db"], db)

    def test_list_merchants_route_passes_filters(self) -> None:
        from app.controllers import ops_dashboard_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())

        try:
            with patch.object(
                ops_dashboard_controller.ops_dashboard_service,
                "list_merchants",
                return_value=MerchantListResponse(
                    merchants=[
                        MerchantListItemResponse(
                            merchant_id="m_demo",
                            merchant_name="Demo Merchant",
                            contact_email="ops@example.com",
                            contact_name="Demo Ops",
                            webhook_url="https://merchant.example.com/webhook",
                            status=MerchantStatus.PENDING_REVIEW,
                            onboarding_status=OnboardingCaseStatus.PENDING_REVIEW,
                            created_at=datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc),
                            updated_at=datetime(2026, 5, 13, 10, 5, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as service:
                response = TestClient(app).get(
                    "/v1/ops/merchants",
                    params={
                        "search": "demo",
                        "status": "PENDING_REVIEW",
                        "onboarding_status": "PENDING_REVIEW",
                        "limit": "25",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["merchants"][0]["merchant_id"], "m_demo")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["search"], "demo")
        self.assertEqual(kwargs["status"], MerchantStatus.PENDING_REVIEW)
        self.assertEqual(kwargs["onboarding_status"], OnboardingCaseStatus.PENDING_REVIEW)
        self.assertEqual(kwargs["limit"], 25)

    def test_list_payments_route_passes_filters(self) -> None:
        from app.controllers import ops_dashboard_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())

        try:
            with patch.object(
                ops_dashboard_controller.ops_dashboard_service,
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
                            expire_at=datetime(2026, 5, 13, 10, 30, tzinfo=timezone.utc),
                            paid_at=datetime(2026, 5, 13, 10, 5, tzinfo=timezone.utc),
                            created_at=datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as service:
                response = TestClient(app).get(
                    "/v1/ops/payments",
                    params={
                        "transaction_id": "pay_demo",
                        "order_id": "ORDER-1",
                        "merchant_id": "m_demo",
                        "status": "SUCCESS",
                        "date_from": "2026-05-12T00:00:00Z",
                        "date_to": "2026-05-13T23:59:59Z",
                        "limit": "10",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["payments"][0]["transaction_id"], "pay_demo")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["transaction_id"], "pay_demo")
        self.assertEqual(kwargs["order_id"], "ORDER-1")
        self.assertEqual(kwargs["merchant_id"], "m_demo")
        self.assertEqual(kwargs["status"], PaymentStatus.SUCCESS)
        self.assertEqual(kwargs["limit"], 10)

    def test_list_webhooks_and_audit_logs_pass_filters(self) -> None:
        from app.controllers import ops_dashboard_controller
        from app.main import app

        db = object()
        entity_id = uuid4()
        actor_id = uuid4()
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())

        try:
            with patch.object(
                ops_dashboard_controller.ops_dashboard_service,
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
                            status=WebhookEventStatus.FAILED,
                            attempt_count=2,
                            next_retry_at=None,
                            last_attempt_at=datetime(2026, 5, 13, 10, 5, tzinfo=timezone.utc),
                            created_at=datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as webhook_service, patch.object(
                ops_dashboard_controller.ops_dashboard_service,
                "list_audit_logs",
                return_value=AuditLogListResponse(
                    logs=[
                        AuditLogItemResponse(
                            log_id=str(uuid4()),
                            event_type="MERCHANT_CREATED",
                            entity_type=EntityType.MERCHANT,
                            entity_id=str(entity_id),
                            actor_type=ActorType.OPS,
                            actor_id=str(actor_id),
                            reason="Created from ops console.",
                            before_state_json=None,
                            after_state_json={"merchant_id": "m_demo"},
                            created_at=datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc),
                        )
                    ]
                ),
            ) as audit_service:
                webhook_response = TestClient(app).get(
                    "/v1/ops/webhooks",
                    params={
                        "event_type": "PAYMENT_COMPLETED",
                        "status": "FAILED",
                        "merchant_id": "m_demo",
                        "limit": "20",
                    },
                )
                audit_response = TestClient(app).get(
                    "/v1/ops/audit-logs",
                    params={
                        "actor_type": "OPS",
                        "actor_id": str(actor_id),
                        "entity_type": "MERCHANT",
                        "entity_id": str(entity_id),
                        "event_type": "MERCHANT_CREATED",
                        "limit": "50",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(webhook_response.status_code, 200)
        self.assertEqual(audit_response.status_code, 200)
        self.assertEqual(webhook_response.json()["events"][0]["event_id"], "evt_demo")
        self.assertEqual(audit_response.json()["logs"][0]["event_type"], "MERCHANT_CREATED")
        self.assertEqual(webhook_service.call_args.kwargs["status"], WebhookEventStatus.FAILED)
        self.assertEqual(audit_service.call_args.kwargs["actor_type"], ActorType.OPS)
        self.assertEqual(audit_service.call_args.kwargs["entity_type"], EntityType.MERCHANT)

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
