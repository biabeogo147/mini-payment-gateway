import unittest
from datetime import timezone
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


class AppFoundationTest(unittest.TestCase):
    def test_health_route_is_registered_from_router_module(self) -> None:
        from app.controllers.health_controller import router as health_router
        from app.main import app

        self.assertEqual(health_router.prefix, "")

        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_get_db_yields_session_and_closes_it(self) -> None:
        from app.controllers import deps

        class FakeSession:
            closed = False

            def close(self) -> None:
                self.closed = True

        fake_session = FakeSession()

        with patch.object(deps, "SessionLocal", return_value=fake_session):
            dependency = deps.get_db()
            self.assertIs(next(dependency), fake_session)
            with self.assertRaises(StopIteration):
                next(dependency)

        self.assertTrue(fake_session.closed)

    def test_app_error_handler_uses_standard_error_shape(self) -> None:
        from app.controllers.errors import app_error_handler
        from app.core.errors import AppError

        local_app = FastAPI()
        local_app.add_exception_handler(AppError, app_error_handler)

        @local_app.get("/boom")
        def boom() -> None:
            raise AppError(
                error_code="PAYMENT_NOT_FOUND",
                message="Payment not found.",
                status_code=404,
                details={"transaction_id": "pay_missing"},
            )

        response = TestClient(local_app).get("/boom")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error_code": "PAYMENT_NOT_FOUND",
                "message": "Payment not found.",
                "details": {"transaction_id": "pay_missing"},
            },
        )

    def test_utc_now_returns_timezone_aware_datetime(self) -> None:
        from app.core.time import utc_now

        now = utc_now()

        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset(), timezone.utc.utcoffset(now))


if __name__ == "__main__":
    unittest.main()
