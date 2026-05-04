import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.enums import DeliveryAttemptResult, WebhookEventStatus
from app.schemas.webhook import WebhookRetryResponse


class WebhookOpsRouteTest(unittest.TestCase):
    def test_manual_retry_route_calls_service_with_db_and_event_id(self) -> None:
        from app.controllers import webhook_ops_controller
        from app.main import app

        db = object()
        response_body = WebhookRetryResponse(
            event_id="evt_123",
            status=WebhookEventStatus.DELIVERED,
            attempt_count=2,
            last_attempt_result=DeliveryAttemptResult.SUCCESS,
            next_retry_at=None,
        )
        self._override_db(app, db)

        try:
            with patch.object(
                webhook_ops_controller.webhook_delivery_service,
                "manual_retry",
                return_value=response_body,
            ) as service:
                response = TestClient(app).post("/v1/ops/webhooks/evt_123/retry")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "event_id": "evt_123",
                "status": "DELIVERED",
                "attempt_count": 2,
                "last_attempt_result": "SUCCESS",
                "next_retry_at": None,
            },
        )
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["event_id"], "evt_123")

    def test_manual_retry_route_serializes_next_retry_at(self) -> None:
        from app.controllers import webhook_ops_controller
        from app.main import app

        db = object()
        next_retry_at = datetime(2026, 4, 29, 10, 1, tzinfo=timezone.utc)
        response_body = WebhookRetryResponse(
            event_id="evt_123",
            status=WebhookEventStatus.PENDING,
            attempt_count=1,
            last_attempt_result=DeliveryAttemptResult.FAILED,
            next_retry_at=next_retry_at,
        )
        self._override_db(app, db)

        try:
            with patch.object(
                webhook_ops_controller.webhook_delivery_service,
                "manual_retry",
                return_value=response_body,
            ):
                response = TestClient(app).post("/v1/ops/webhooks/evt_123/retry")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["next_retry_at"], "2026-04-29T10:01:00Z")

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
