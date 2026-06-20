import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.enums import InternalUserRole, MerchantUserStatus
from tests.internal_auth_test_utils import make_internal_user, override_current_internal_user
from tests.merchant_portal_test_utils import make_merchant_user


class OpsMerchantPortalUserRouteTest(unittest.TestCase):
    def test_admin_and_ops_can_list_create_update_and_reset_merchant_portal_users(self) -> None:
        from app.controllers import ops_merchant_portal_user_controller
        from app.main import app
        from app.schemas.merchant_portal import (
            MerchantPortalGeneratedPasswordResponse,
            MerchantPortalUserListResponse,
            MerchantPortalUserResponse,
        )

        for role in (InternalUserRole.ADMIN, InternalUserRole.OPS):
            with self.subTest(role=role.value):
                db = object()
                portal_user = make_merchant_user(email="merchant@example.com")
                current_user = make_internal_user(role=role)
                self._override_db(app, db)
                override_current_internal_user(app, current_user)

                try:
                    with patch.object(
                        ops_merchant_portal_user_controller.merchant_portal_user_ops_service,
                        "list_users",
                        return_value=MerchantPortalUserListResponse(
                            users=[MerchantPortalUserResponse.from_user(portal_user)]
                        ),
                    ) as list_service, patch.object(
                        ops_merchant_portal_user_controller.merchant_portal_user_ops_service,
                        "create_user",
                        return_value=MerchantPortalGeneratedPasswordResponse(
                            user=MerchantPortalUserResponse.from_user(portal_user),
                            generated_password="generated-secret",
                        ),
                    ) as create_service, patch.object(
                        ops_merchant_portal_user_controller.merchant_portal_user_ops_service,
                        "update_user",
                        return_value=MerchantPortalUserResponse.from_user(portal_user),
                    ) as update_service, patch.object(
                        ops_merchant_portal_user_controller.merchant_portal_user_ops_service,
                        "reset_password",
                        return_value=MerchantPortalGeneratedPasswordResponse(
                            user=MerchantPortalUserResponse.from_user(portal_user),
                            generated_password="reset-secret",
                        ),
                    ) as reset_service:
                        list_response = TestClient(app).get(
                            "/v1/ops/merchants/m_demo/portal-users"
                        )
                        create_response = TestClient(app).post(
                            "/v1/ops/merchants/m_demo/portal-users",
                            json={
                                "email": "merchant@example.com",
                                "full_name": "Merchant User",
                                "role": "MERCHANT_ADMIN",
                                "status": "ACTIVE",
                            },
                        )
                        update_response = TestClient(app).patch(
                            f"/v1/ops/merchants/m_demo/portal-users/{portal_user.id}",
                            json={"status": "INACTIVE"},
                        )
                        reset_response = TestClient(app).post(
                            f"/v1/ops/merchants/m_demo/portal-users/{portal_user.id}/reset-password"
                        )
                finally:
                    app.dependency_overrides.clear()

                self.assertEqual(list_response.status_code, 200)
                self.assertEqual(create_response.status_code, 200)
                self.assertEqual(update_response.status_code, 200)
                self.assertEqual(reset_response.status_code, 200)
                self.assertEqual(
                    list_response.json()["users"][0]["email"],
                    "merchant@example.com",
                )
                self.assertEqual(
                    create_response.json()["generated_password"],
                    "generated-secret",
                )
                self.assertEqual(
                    reset_response.json()["generated_password"],
                    "reset-secret",
                )
                self.assertIs(list_service.call_args.kwargs["db"], db)
                self.assertEqual(create_service.call_args.kwargs["current_user"].id, current_user.id)
                self.assertEqual(create_service.call_args.kwargs["merchant_id"], "m_demo")
                self.assertEqual(
                    update_service.call_args.kwargs["status"],
                    MerchantUserStatus.INACTIVE,
                )
                self.assertEqual(reset_service.call_args.kwargs["merchant_id"], "m_demo")

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


if __name__ == "__main__":
    unittest.main()
