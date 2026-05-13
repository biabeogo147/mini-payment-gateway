import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.enums import InternalUserRole, InternalUserStatus
from app.schemas.internal_auth import InternalUserListResponse, InternalUserResponse
from tests.internal_auth_test_utils import make_internal_user, override_current_internal_user


class InternalUserRouteTest(unittest.TestCase):
    def test_list_users_route_calls_service_for_admin(self) -> None:
        from app.controllers import internal_user_controller
        from app.main import app

        db = object()
        admin_user = make_internal_user(role=InternalUserRole.ADMIN)
        self._override_db(app, db)
        override_current_internal_user(app, admin_user)

        try:
            with patch.object(
                internal_user_controller.internal_user_admin_service,
                "list_users",
                return_value=InternalUserListResponse(users=[InternalUserResponse.from_user(admin_user)]),
            ) as service:
                response = TestClient(app).get("/v1/internal/users")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["users"][0]["email"], admin_user.email)
        self.assertIs(service.call_args.args[0], db)

    def test_list_users_route_rejects_ops_user(self) -> None:
        from app.main import app

        override_current_internal_user(app, make_internal_user(role=InternalUserRole.OPS))

        try:
            response = TestClient(app).get("/v1/internal/users")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error_code"], "INTERNAL_AUTH_FORBIDDEN")

    def test_mutation_routes_pass_request_and_current_user(self) -> None:
        from app.controllers import internal_user_controller
        from app.main import app

        db = object()
        admin_user = make_internal_user(role=InternalUserRole.ADMIN)
        managed_user = make_internal_user(email="managed@example.com")
        self._override_db(app, db)
        override_current_internal_user(app, admin_user)

        cases = (
            (
                "post",
                "/v1/internal/users",
                "create_user",
                {
                    "email": "managed@example.com",
                    "full_name": "Managed User",
                    "role": "OPS",
                    "password": "managed-pass",
                    "status": "ACTIVE",
                },
            ),
            (
                "patch",
                f"/v1/internal/users/{managed_user.id}",
                "update_user",
                {"full_name": "Managed User Updated", "status": "INACTIVE"},
            ),
            (
                "post",
                f"/v1/internal/users/{managed_user.id}/reset-password",
                "reset_password",
                {"new_password": "brand-new-password"},
            ),
        )

        try:
            for method, path, service_name, body in cases:
                with self.subTest(path=path):
                    with patch.object(
                        internal_user_controller.internal_user_admin_service,
                        service_name,
                        return_value=InternalUserResponse.from_user(managed_user),
                    ) as service:
                        response = getattr(TestClient(app), method)(path, json=body)

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["email"], "managed@example.com")
                    kwargs = service.call_args.kwargs
                    self.assertIs(kwargs["db"], db)
                    self.assertEqual(kwargs["current_user"].id, admin_user.id)
        finally:
            app.dependency_overrides.clear()

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
