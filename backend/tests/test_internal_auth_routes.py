import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.enums import InternalUserRole
from app.schemas.internal_auth import InternalAuthSessionResponse, InternalUserResponse
from tests.internal_auth_test_utils import make_internal_user, override_current_internal_user


class InternalAuthRouteTest(unittest.TestCase):
    def test_bootstrap_status_route_reads_service_result(self) -> None:
        from app.controllers import internal_auth_controller
        from app.main import app

        self._override_db(app, object())

        try:
            with patch.object(
                internal_auth_controller.internal_auth_service,
                "bootstrap_required",
                return_value=True,
            ):
                response = TestClient(app).get("/v1/internal/auth/bootstrap-status")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"bootstrap_required": True})

    def test_bootstrap_route_sets_session_cookie(self) -> None:
        from app.controllers import internal_auth_controller
        from app.main import app

        db = object()
        admin_user = make_internal_user(role=InternalUserRole.ADMIN, email="admin@example.com")
        self._override_db(app, db)

        try:
            with patch.object(
                internal_auth_controller.internal_auth_service,
                "bootstrap_first_admin",
                return_value=(admin_user, "bootstrap-token"),
            ) as service:
                response = TestClient(app).post(
                    "/v1/internal/auth/bootstrap",
                    json={
                        "email": "admin@example.com",
                        "full_name": "Admin User",
                        "password": "super-secret",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "admin@example.com")
        self.assertIn("mini_payment_gateway_internal_session=bootstrap-token", response.headers["set-cookie"])
        self.assertIs(service.call_args.kwargs["db"], db)

    def test_login_route_sets_session_cookie(self) -> None:
        from app.controllers import internal_auth_controller
        from app.main import app

        db = object()
        ops_user = make_internal_user(email="ops@example.com")
        self._override_db(app, db)

        try:
            with patch.object(
                internal_auth_controller.internal_auth_service,
                "login",
                return_value=(ops_user, "login-token"),
            ) as service:
                response = TestClient(app).post(
                    "/v1/internal/auth/login",
                    json={"email": "ops@example.com", "password": "super-secret"},
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "ops@example.com")
        self.assertIn("mini_payment_gateway_internal_session=login-token", response.headers["set-cookie"])
        self.assertIs(service.call_args.kwargs["db"], db)

    def test_logout_route_clears_session_cookie(self) -> None:
        from app.main import app

        response = TestClient(app).post("/v1/internal/auth/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIn("mini_payment_gateway_internal_session=", response.headers["set-cookie"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_me_route_serializes_current_user(self) -> None:
        from app.main import app

        current_user = make_internal_user(email="ops@example.com")
        override_current_internal_user(app, current_user)

        try:
            response = TestClient(app).get("/v1/internal/auth/me")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["user_id"], str(current_user.id))
        self.assertEqual(response.json()["user"]["email"], "ops@example.com")

    def test_change_password_route_uses_current_user_and_sets_new_cookie(self) -> None:
        from app.controllers import internal_auth_controller
        from app.main import app

        db = object()
        current_user = make_internal_user(email="ops@example.com")
        self._override_db(app, db)
        override_current_internal_user(app, current_user)

        try:
            with patch.object(
                internal_auth_controller.internal_auth_service,
                "change_password",
                return_value=(current_user, "changed-token"),
            ) as service:
                response = TestClient(app).post(
                    "/v1/internal/auth/change-password",
                    json={
                        "current_password": "old-secret",
                        "new_password": "new-super-secret",
                    },
                )
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "ops@example.com")
        self.assertIn("mini_payment_gateway_internal_session=changed-token", response.headers["set-cookie"])
        self.assertIs(service.call_args.kwargs["db"], db)
        self.assertEqual(service.call_args.kwargs["current_user"].id, current_user.id)

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
