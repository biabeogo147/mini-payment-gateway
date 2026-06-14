import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.enums import MerchantStatus
from tests.merchant_portal_test_utils import make_merchant, make_merchant_user, override_current_merchant_user


class MerchantPortalAuthRouteTest(unittest.TestCase):
    def test_login_route_sets_merchant_session_cookie(self) -> None:
        from app.controllers import merchant_portal_auth_controller
        from app.main import app

        db = object()
        merchant_user = make_merchant_user(email="merchant@example.com")
        self._override_db(app, db)

        try:
            with patch.object(
                merchant_portal_auth_controller.merchant_portal_auth_service,
                "login",
                return_value=(merchant_user, "merchant-login-token"),
            ) as service:
                response = TestClient(app).post(
                    "/v1/merchant-portal/auth/login",
                    json={
                        "merchant_id": "m_demo",
                        "email": "merchant@example.com",
                        "password": "super-secret",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "merchant@example.com")
        self.assertEqual(response.json()["user"]["merchant_id"], "m_demo")
        self.assertIn(
            "mini_payment_gateway_merchant_session=merchant-login-token",
            response.headers["set-cookie"],
        )
        self.assertIs(service.call_args.kwargs["db"], db)
        self.assertEqual(service.call_args.kwargs["request"].merchant_id, "m_demo")

    def test_logout_route_clears_merchant_session_cookie(self) -> None:
        from app.main import app

        response = TestClient(app).post("/v1/merchant-portal/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("mini_payment_gateway_merchant_session=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_me_route_serializes_current_merchant_user(self) -> None:
        from app.main import app

        merchant = make_merchant(status=MerchantStatus.DISABLED)
        current_user = make_merchant_user(merchant=merchant, email="merchant@example.com")
        override_current_merchant_user(app, current_user)

        try:
            response = TestClient(app).get("/v1/merchant-portal/auth/me")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["user_id"], str(current_user.id))
        self.assertEqual(response.json()["user"]["merchant_id"], "m_demo")
        self.assertEqual(response.json()["merchant_status"], "DISABLED")

    def test_change_password_route_uses_current_merchant_user_and_sets_cookie(self) -> None:
        from app.controllers import merchant_portal_auth_controller
        from app.main import app

        db = object()
        current_user = make_merchant_user(email="merchant@example.com")
        self._override_db(app, db)
        override_current_merchant_user(app, current_user)

        try:
            with patch.object(
                merchant_portal_auth_controller.merchant_portal_auth_service,
                "change_password",
                return_value=(current_user, "changed-token"),
            ) as service:
                response = TestClient(app).post(
                    "/v1/merchant-portal/auth/change-password",
                    json={
                        "current_password": "old-secret",
                        "new_password": "new-super-secret",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "merchant@example.com")
        self.assertIn(
            "mini_payment_gateway_merchant_session=changed-token",
            response.headers["set-cookie"],
        )
        self.assertIs(service.call_args.kwargs["db"], db)
        self.assertEqual(service.call_args.kwargs["current_user"].id, current_user.id)

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
