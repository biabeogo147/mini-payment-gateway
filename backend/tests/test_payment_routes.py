import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import CredentialStatus, MerchantStatus, PaymentStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.payment import PaymentResponse, PaymentStatusResponse


class PaymentRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authenticated = AuthenticatedMerchant(
            merchant=Merchant(
                id=uuid4(),
                merchant_id="m_demo",
                merchant_name="Demo Merchant",
                contact_email="ops@example.com",
                status=MerchantStatus.ACTIVE,
            ),
            credential=MerchantCredential(
                id=uuid4(),
                merchant_db_id=uuid4(),
                access_key="ak_demo",
                secret_key_encrypted="super-secret",
                secret_key_last4="cret",
                status=CredentialStatus.ACTIVE,
            ),
            merchant_id="m_demo",
        )
        self.response = PaymentResponse(
            transaction_id="pay_123",
            order_id="ORDER-1001",
            merchant_id="m_demo",
            qr_content="MINI_GATEWAY|merchant_id=m_demo|transaction_id=pay_123|amount=100000.00|currency=VND",
            status=PaymentStatus.PENDING,
            expire_at=datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc),
        )

    def test_create_payment_route_calls_service_with_auth_and_idempotency_key(self) -> None:
        from app.controllers import payment_controller
        from app.main import app

        db = object()
        self._override_dependencies(app, db)

        try:
            with patch.object(payment_controller.payment_service, "create_payment", return_value=self.response) as service:
                response = TestClient(app).post(
                    "/v1/payments",
                    json={
                        "order_id": "ORDER-1001",
                        "amount": "100000.00",
                        "description": "Demo QR payment",
                        "ttl_seconds": 900,
                    },
                    headers={"X-Idempotency-Key": "idem-1"},
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transaction_id"], "pay_123")
        self.assertEqual(response.json()["status"], "PENDING")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertIs(kwargs["authenticated_merchant"], self.authenticated)
        self.assertEqual(kwargs["idempotency_key"], "idem-1")
        self.assertEqual(kwargs["request"].order_id, "ORDER-1001")

    def test_get_payment_by_transaction_route_returns_status(self) -> None:
        from app.controllers import payment_controller
        from app.main import app

        db = object()
        self._override_dependencies(app, db)

        try:
            with patch.object(
                payment_controller.payment_service,
                "get_payment_by_transaction_id",
                return_value=PaymentStatusResponse(**self.response.model_dump()),
            ) as service:
                response = TestClient(app).get("/v1/payments/pay_123")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["transaction_id"], "pay_123")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertIs(kwargs["authenticated_merchant"], self.authenticated)
        self.assertEqual(kwargs["transaction_id"], "pay_123")

    def test_get_payment_by_order_route_is_not_shadowed_by_transaction_route(self) -> None:
        from app.controllers import payment_controller
        from app.main import app

        db = object()
        self._override_dependencies(app, db)

        try:
            with patch.object(
                payment_controller.payment_service,
                "get_payment_by_order_id",
                return_value=PaymentStatusResponse(**self.response.model_dump()),
            ) as service:
                response = TestClient(app).get("/v1/payments/by-order/ORDER-1001")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["order_id"], "ORDER-1001")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertIs(kwargs["authenticated_merchant"], self.authenticated)
        self.assertEqual(kwargs["order_id"], "ORDER-1001")

    def _override_dependencies(self, app, db) -> None:
        from app.controllers.deps import get_authenticated_merchant, get_db

        def db_override():
            return db

        async def authenticated_override():
            return self.authenticated

        app.dependency_overrides[get_db] = db_override
        app.dependency_overrides[get_authenticated_merchant] = authenticated_override


if __name__ == "__main__":
    unittest.main()
