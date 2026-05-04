import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import CredentialStatus, MerchantStatus, RefundStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.schemas.auth import AuthenticatedMerchant
from app.schemas.refund import RefundResponse, RefundStatusResponse


class RefundRouteTest(unittest.TestCase):
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
        self.response = RefundResponse(
            refund_transaction_id="rfnd_123",
            original_transaction_id="pay_123",
            refund_id="REF-1001",
            refund_amount=Decimal("100000.00"),
            refund_status=RefundStatus.REFUND_PENDING,
        )

    def test_create_refund_route_calls_service_with_auth_and_idempotency_key(self) -> None:
        from app.controllers import refund_controller
        from app.main import app

        db = object()
        self._override_dependencies(app, db)

        try:
            with patch.object(refund_controller.refund_service, "create_refund", return_value=self.response) as service:
                response = TestClient(app).post(
                    "/v1/refunds",
                    json={
                        "original_transaction_id": "pay_123",
                        "refund_id": "REF-1001",
                        "refund_amount": "100000.00",
                        "reason": "Customer requested refund",
                    },
                    headers={"X-Idempotency-Key": "idem-refund-1"},
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["refund_transaction_id"], "rfnd_123")
        self.assertEqual(response.json()["refund_status"], "REFUND_PENDING")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertIs(kwargs["authenticated_merchant"], self.authenticated)
        self.assertEqual(kwargs["idempotency_key"], "idem-refund-1")
        self.assertEqual(kwargs["request"].refund_id, "REF-1001")

    def test_get_refund_by_refund_id_route_is_not_shadowed_by_transaction_route(self) -> None:
        from app.controllers import refund_controller
        from app.main import app

        db = object()
        self._override_dependencies(app, db)

        try:
            with patch.object(
                refund_controller.refund_service,
                "get_refund_by_refund_id",
                return_value=RefundStatusResponse(**self.response.model_dump()),
            ) as service:
                response = TestClient(app).get("/v1/refunds/by-refund-id/REF-1001")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["refund_id"], "REF-1001")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertIs(kwargs["authenticated_merchant"], self.authenticated)
        self.assertEqual(kwargs["refund_id"], "REF-1001")

    def test_get_refund_by_transaction_route_returns_status(self) -> None:
        from app.controllers import refund_controller
        from app.main import app

        db = object()
        self._override_dependencies(app, db)

        try:
            with patch.object(
                refund_controller.refund_service,
                "get_refund_by_transaction_id",
                return_value=RefundStatusResponse(**self.response.model_dump()),
            ) as service:
                response = TestClient(app).get("/v1/refunds/rfnd_123")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["refund_transaction_id"], "rfnd_123")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertIs(kwargs["authenticated_merchant"], self.authenticated)
        self.assertEqual(kwargs["refund_transaction_id"], "rfnd_123")

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
