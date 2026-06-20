import unittest
from unittest.mock import MagicMock, patch

from app.core.errors import AppError
from app.models.enums import ActorType, InternalUserRole, MerchantUserRole, MerchantUserStatus
from app.schemas.merchant_portal import CreateMerchantPortalUserRequest
from tests.internal_auth_test_utils import make_internal_user
from tests.merchant_portal_test_utils import make_merchant, make_merchant_user


class MerchantPortalUserOpsServiceTest(unittest.TestCase):
    def test_ops_can_create_user_and_audit_records_ops_actor_without_password(self) -> None:
        from app.services import merchant_portal_user_ops_service

        db = MagicMock()
        merchant = make_merchant()
        portal_user = make_merchant_user(merchant=merchant, email="merchant@example.com")
        ops_user = make_internal_user(role=InternalUserRole.OPS)
        request = CreateMerchantPortalUserRequest(
            email="merchant@example.com",
            full_name="Merchant User",
            role=MerchantUserRole.MERCHANT_ADMIN,
            status=MerchantUserStatus.ACTIVE,
        )

        with patch.object(
            merchant_portal_user_ops_service,
            "_require_merchant",
            return_value=merchant,
        ), patch.object(
            merchant_portal_user_ops_service.merchant_user_repository,
            "get_by_merchant_and_email",
            return_value=None,
        ), patch.object(
            merchant_portal_user_ops_service.merchant_user_repository,
            "create",
            return_value=portal_user,
        ), patch.object(
            merchant_portal_user_ops_service,
            "_generate_password",
            return_value="temporary-secret",
        ), patch.object(
            merchant_portal_user_ops_service,
            "hash_password",
            return_value="hashed-secret",
        ), patch.object(
            merchant_portal_user_ops_service.audit_service,
            "record_event",
        ) as record_event:
            response = merchant_portal_user_ops_service.create_user(
                db=db,
                current_user=ops_user,
                merchant_id="m_demo",
                request=request,
            )

        self.assertEqual(response.generated_password, "temporary-secret")
        audit = record_event.call_args.kwargs
        self.assertEqual(audit["actor_type"], ActorType.OPS)
        self.assertEqual(audit["actor_id"], ops_user.id)
        self.assertNotIn("temporary-secret", str(audit))

    def test_ops_can_update_user_and_audit_records_ops_actor(self) -> None:
        from app.services import merchant_portal_user_ops_service

        db = MagicMock()
        merchant = make_merchant()
        portal_user = make_merchant_user(merchant=merchant, email="merchant@example.com")
        ops_user = make_internal_user(role=InternalUserRole.OPS)

        with patch.object(
            merchant_portal_user_ops_service,
            "_require_merchant",
            return_value=merchant,
        ), patch.object(
            merchant_portal_user_ops_service,
            "_require_user",
            return_value=portal_user,
        ), patch.object(
            merchant_portal_user_ops_service.merchant_user_repository,
            "save",
            return_value=portal_user,
        ), patch.object(
            merchant_portal_user_ops_service.audit_service,
            "record_event",
        ) as record_event:
            response = merchant_portal_user_ops_service.update_user(
                db=db,
                current_user=ops_user,
                merchant_id="m_demo",
                user_id=str(portal_user.id),
                status=MerchantUserStatus.INACTIVE,
            )

        self.assertEqual(response.status, MerchantUserStatus.INACTIVE)
        audit = record_event.call_args.kwargs
        self.assertEqual(audit["actor_type"], ActorType.OPS)
        self.assertEqual(audit["actor_id"], ops_user.id)

    def test_ops_can_reset_password_and_audit_does_not_expose_password(self) -> None:
        from app.services import merchant_portal_user_ops_service

        db = MagicMock()
        merchant = make_merchant()
        portal_user = make_merchant_user(merchant=merchant, email="merchant@example.com")
        ops_user = make_internal_user(role=InternalUserRole.OPS)

        with patch.object(
            merchant_portal_user_ops_service,
            "_require_merchant",
            return_value=merchant,
        ), patch.object(
            merchant_portal_user_ops_service,
            "_require_user",
            return_value=portal_user,
        ), patch.object(
            merchant_portal_user_ops_service,
            "_generate_password",
            return_value="reset-temporary-secret",
        ), patch.object(
            merchant_portal_user_ops_service,
            "hash_password",
            return_value="reset-hashed-secret",
        ), patch.object(
            merchant_portal_user_ops_service.merchant_user_repository,
            "save",
            return_value=portal_user,
        ), patch.object(
            merchant_portal_user_ops_service.audit_service,
            "record_event",
        ) as record_event:
            response = merchant_portal_user_ops_service.reset_password(
                db=db,
                current_user=ops_user,
                merchant_id="m_demo",
                user_id=str(portal_user.id),
            )

        self.assertEqual(response.generated_password, "reset-temporary-secret")
        audit = record_event.call_args.kwargs
        self.assertEqual(audit["actor_type"], ActorType.OPS)
        self.assertEqual(audit["actor_id"], ops_user.id)
        self.assertNotIn("reset-temporary-secret", str(audit))

    def test_create_user_preserves_duplicate_error_for_ops(self) -> None:
        from app.services import merchant_portal_user_ops_service

        db = MagicMock()
        merchant = make_merchant()
        portal_user = make_merchant_user(merchant=merchant, email="merchant@example.com")
        ops_user = make_internal_user(role=InternalUserRole.OPS)
        request = CreateMerchantPortalUserRequest(
            email="merchant@example.com",
            full_name="Merchant User",
            role=MerchantUserRole.MERCHANT_ADMIN,
            status=MerchantUserStatus.ACTIVE,
        )

        with patch.object(
            merchant_portal_user_ops_service,
            "_require_merchant",
            return_value=merchant,
        ), patch.object(
            merchant_portal_user_ops_service.merchant_user_repository,
            "get_by_merchant_and_email",
            return_value=portal_user,
        ):
            with self.assertRaises(AppError) as raised:
                merchant_portal_user_ops_service.create_user(
                    db=db,
                    current_user=ops_user,
                    merchant_id="m_demo",
                    request=request,
                )

        self.assertEqual(raised.exception.error_code, "MERCHANT_PORTAL_USER_ALREADY_EXISTS")
        self.assertEqual(raised.exception.status_code, 409)

    def test_require_user_preserves_not_found_error(self) -> None:
        from app.services import merchant_portal_user_ops_service

        with patch.object(
            merchant_portal_user_ops_service.merchant_user_repository,
            "get_by_merchant_and_id",
            return_value=None,
        ):
            with self.assertRaises(AppError) as raised:
                merchant_portal_user_ops_service._require_user(
                    MagicMock(),
                    make_merchant().id,
                    "missing-user",
                )

        self.assertEqual(raised.exception.error_code, "MERCHANT_PORTAL_USER_NOT_FOUND")
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
