import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import CallbackProcessingResult, PaymentStatus, RefundStatus
from app.schemas.provider_callback import PaymentCallbackResponse, RefundCallbackResponse


class ProviderCallbackRouteTest(unittest.TestCase):
    def test_payment_callback_route_calls_service_with_db_and_request(self) -> None:
        from app.controllers import provider_callback_controller
        from app.main import app

        db = object()
        response_body = PaymentCallbackResponse(
            transaction_id="pay_123",
            status=PaymentStatus.SUCCESS,
            processing_result=CallbackProcessingResult.PROCESSED,
            reconciliation_record_id=None,
        )
        self._override_db(app, db)

        try:
            with patch.object(
                provider_callback_controller.provider_callback_service,
                "process_payment_callback",
                return_value=response_body,
            ) as service:
                response = TestClient(app).post(
                    "/v1/provider/callbacks/payment",
                    json={
                        "external_reference": "bank-ref-1001",
                        "transaction_reference": "pay_123",
                        "status": "SUCCESS",
                        "amount": "100000.00",
                        "paid_at": "2026-04-29T10:05:00Z",
                        "raw_payload": {"trace_id": "trace-1001"},
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "transaction_id": "pay_123",
                "status": "SUCCESS",
                "processing_result": "PROCESSED",
                "reconciliation_record_id": None,
            },
        )
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["request"].transaction_reference, "pay_123")
        self.assertEqual(kwargs["request"].raw_payload, {"trace_id": "trace-1001"})

    def test_payment_callback_route_serializes_reconciliation_record_id(self) -> None:
        from app.controllers import provider_callback_controller
        from app.main import app

        db = object()
        reconciliation_record_id = uuid4()
        response_body = PaymentCallbackResponse(
            transaction_id="pay_123",
            status=PaymentStatus.EXPIRED,
            processing_result=CallbackProcessingResult.PENDING_REVIEW,
            reconciliation_record_id=str(reconciliation_record_id),
        )
        self._override_db(app, db)

        try:
            with patch.object(
                provider_callback_controller.provider_callback_service,
                "process_payment_callback",
                return_value=response_body,
            ):
                response = TestClient(app).post(
                    "/v1/provider/callbacks/payment",
                    json={
                        "external_reference": "bank-ref-1001",
                        "transaction_reference": "pay_123",
                        "status": "SUCCESS",
                        "amount": "100000.00",
                        "paid_at": datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc).isoformat(),
                        "raw_payload": {"trace_id": "trace-1001"},
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reconciliation_record_id"], str(reconciliation_record_id))
        self.assertEqual(response.json()["processing_result"], "PENDING_REVIEW")

    def test_refund_callback_route_calls_service_with_db_and_request(self) -> None:
        from app.controllers import provider_callback_controller
        from app.main import app

        db = object()
        response_body = RefundCallbackResponse(
            refund_transaction_id="rfnd_123",
            refund_status=RefundStatus.REFUNDED,
            processing_result=CallbackProcessingResult.PROCESSED,
            reconciliation_record_id=None,
        )
        self._override_db(app, db)

        try:
            with patch.object(
                provider_callback_controller.provider_callback_service,
                "process_refund_callback",
                return_value=response_body,
            ) as service:
                response = TestClient(app).post(
                    "/v1/provider/callbacks/refund",
                    json={
                        "external_reference": "bank-refund-1001",
                        "refund_transaction_id": "rfnd_123",
                        "status": "SUCCESS",
                        "amount": "100000.00",
                        "processed_at": "2026-04-29T10:05:00Z",
                        "raw_payload": {"trace_id": "refund-trace-1001"},
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "refund_transaction_id": "rfnd_123",
                "refund_status": "REFUNDED",
                "processing_result": "PROCESSED",
                "reconciliation_record_id": None,
            },
        )
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["request"].refund_transaction_id, "rfnd_123")
        self.assertEqual(kwargs["request"].raw_payload, {"trace_id": "refund-trace-1001"})

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
