import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import CredentialStatus, InternalUserRole, MerchantQrAccountStatus, MerchantStatus, OnboardingCaseStatus, QrProvider
from app.schemas.ops import CredentialOpsResponse, MerchantOpsResponse, OnboardingCaseResponse, QrAccountOpsResponse
from tests.internal_auth_test_utils import make_internal_user, override_current_internal_user


class MerchantOpsRouteTest(unittest.TestCase):
    def test_create_merchant_route_calls_service_with_request_db_and_actor(self) -> None:
        from app.controllers import ops_merchant_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())
        response_body = MerchantOpsResponse(
            merchant_id="m_demo",
            merchant_name="Demo Merchant",
            status=MerchantStatus.PENDING_REVIEW,
        )

        try:
            with patch.object(
                ops_merchant_controller.merchant_ops_service,
                "create_merchant",
                return_value=response_body,
            ) as service:
                response = TestClient(app).post("/v1/ops/merchants", json=_create_merchant_json())
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["merchant_id"], "m_demo")
        self.assertEqual(response.json()["status"], "PENDING_REVIEW")
        kwargs = service.call_args.kwargs
        self.assertIs(kwargs["db"], db)
        self.assertEqual(kwargs["request"].merchant_id, "m_demo")
        self.assertEqual(kwargs["actor"].reason, "Ops action.")

    def test_onboarding_routes_call_service_with_merchant_id_and_actor(self) -> None:
        from app.controllers import ops_merchant_controller
        from app.main import app

        db = object()
        case_id = uuid4()
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())

        route_cases = (
            (
                "put",
                "/v1/ops/merchants/m_demo/onboarding-case",
                "submit_onboarding_case",
                _submit_onboarding_json(),
                OnboardingCaseResponse(
                    case_id=str(case_id),
                    merchant_id="m_demo",
                    status=OnboardingCaseStatus.PENDING_REVIEW,
                    domain_or_app_name="Demo Shop",
                ),
            ),
            (
                "post",
                "/v1/ops/merchants/m_demo/onboarding-case/approve",
                "approve_onboarding_case",
                _review_onboarding_json("Documents verified."),
                OnboardingCaseResponse(
                    case_id=str(case_id),
                    merchant_id="m_demo",
                    status=OnboardingCaseStatus.APPROVED,
                    reviewed_by=uuid4(),
                    reviewed_at=datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc),
                    decision_note="Documents verified.",
                ),
            ),
            (
                "post",
                "/v1/ops/merchants/m_demo/onboarding-case/reject",
                "reject_onboarding_case",
                _review_onboarding_json("Risk policy mismatch."),
                OnboardingCaseResponse(
                    case_id=str(case_id),
                    merchant_id="m_demo",
                    status=OnboardingCaseStatus.REJECTED,
                    decision_note="Risk policy mismatch.",
                ),
            ),
        )

        try:
            for method, path, service_name, body, service_response in route_cases:
                with self.subTest(path=path):
                    with patch.object(
                        ops_merchant_controller.merchant_ops_service,
                        service_name,
                        return_value=service_response,
                    ) as service:
                        response = getattr(TestClient(app), method)(path, json=body)

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["merchant_id"], "m_demo")
                    kwargs = service.call_args.kwargs
                    self.assertIs(kwargs["db"], db)
                    self.assertEqual(kwargs["merchant_id"], "m_demo")
                    self.assertEqual(kwargs["actor"].actor_type.value, "OPS")
        finally:
            app.dependency_overrides.clear()

    def test_credential_routes_call_service_with_merchant_id_and_actor(self) -> None:
        from app.controllers import ops_merchant_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
        response_body = CredentialOpsResponse(
            credential_id=str(uuid4()),
            merchant_id="m_demo",
            access_key="ak_new",
            secret_key_last4="cret",
            status=CredentialStatus.ACTIVE,
        )

        route_cases = (
            (
                "/v1/ops/merchants/m_demo/credentials",
                "create_credential",
                _credential_json("ak_new"),
                make_internal_user(),
                200,
            ),
            (
                "/v1/ops/merchants/m_demo/credentials/rotate",
                "rotate_credential",
                _credential_json("ak_rotated"),
                make_internal_user(role=InternalUserRole.ADMIN),
                200,
            ),
        )

        try:
            for path, service_name, body, current_user, expected_status_code in route_cases:
                with self.subTest(path=path):
                    override_current_internal_user(app, current_user)
                    with patch.object(
                        ops_merchant_controller.merchant_ops_service,
                        service_name,
                        return_value=response_body,
                    ) as service:
                        response = TestClient(app).post(path, json=body)

                    self.assertEqual(response.status_code, expected_status_code)
                    self.assertEqual(response.json()["access_key"], "ak_new")
                    self.assertNotIn("secret_key", response.json())
                    kwargs = service.call_args.kwargs
                    self.assertIs(kwargs["db"], db)
                    self.assertEqual(kwargs["merchant_id"], "m_demo")
                    self.assertEqual(kwargs["actor"].reason, "Ops action.")
        finally:
            app.dependency_overrides.clear()

    def test_status_routes_call_service_with_merchant_id_and_actor(self) -> None:
        from app.controllers import ops_merchant_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
        route_cases = (
            (
                "/v1/ops/merchants/m_demo/activate",
                "activate_merchant",
                MerchantStatus.ACTIVE,
                make_internal_user(),
                200,
            ),
            (
                "/v1/ops/merchants/m_demo/suspend",
                "suspend_merchant",
                MerchantStatus.SUSPENDED,
                make_internal_user(),
                200,
            ),
            (
                "/v1/ops/merchants/m_demo/disable",
                "disable_merchant",
                MerchantStatus.DISABLED,
                make_internal_user(role=InternalUserRole.ADMIN),
                200,
            ),
        )

        try:
            for path, service_name, expected_status, current_user, expected_status_code in route_cases:
                with self.subTest(path=path):
                    override_current_internal_user(app, current_user)
                    response_body = MerchantOpsResponse(
                        merchant_id="m_demo",
                        merchant_name="Demo Merchant",
                        status=expected_status,
                    )
                    with patch.object(
                        ops_merchant_controller.merchant_ops_service,
                        service_name,
                        return_value=response_body,
                    ) as service:
                        response = TestClient(app).post(path, json=_reason_json())

                    self.assertEqual(response.status_code, expected_status_code)
                    self.assertEqual(response.json()["status"], expected_status.value)
                    kwargs = service.call_args.kwargs
                    self.assertIs(kwargs["db"], db)
                    self.assertEqual(kwargs["merchant_id"], "m_demo")
                    expected_actor_type = "ADMIN" if current_user.role.value == "ADMIN" else "OPS"
                    self.assertEqual(kwargs["actor"].actor_type.value, expected_actor_type)
        finally:
            app.dependency_overrides.clear()

    def test_qr_account_routes_call_service_with_merchant_id_and_actor(self) -> None:
        from app.controllers import ops_merchant_controller
        from app.main import app

        db = object()
        qr_account_id = str(uuid4())
        self._override_db(app, db)
        override_current_internal_user(app, make_internal_user())
        response_body = QrAccountOpsResponse(
            qr_account_id=qr_account_id,
            merchant_id="m_demo",
            provider=QrProvider.VIETQR,
            bank_code="VCB",
            bank_bin="970436",
            account_number="9704361234567890",
            account_name="DEMO MERCHANT LLC",
            template="compact",
            status=MerchantQrAccountStatus.ACTIVE,
        )

        route_cases = (
            (
                "post",
                "/v1/ops/merchants/m_demo/qr-accounts",
                "create_qr_account",
                _qr_account_json(),
            ),
            (
                "patch",
                f"/v1/ops/merchants/m_demo/qr-accounts/{qr_account_id}",
                "update_qr_account",
                _qr_account_update_json(),
            ),
            (
                "post",
                f"/v1/ops/merchants/m_demo/qr-accounts/{qr_account_id}/activate",
                "activate_qr_account",
                _reason_json(),
            ),
            (
                "post",
                f"/v1/ops/merchants/m_demo/qr-accounts/{qr_account_id}/deactivate",
                "deactivate_qr_account",
                _reason_json(),
            ),
        )

        try:
            for method, path, service_name, body in route_cases:
                with self.subTest(path=path):
                    with patch.object(
                        ops_merchant_controller.merchant_ops_service,
                        service_name,
                        return_value=response_body,
                    ) as service:
                        response = getattr(TestClient(app), method)(path, json=body)

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["qr_account_id"], qr_account_id)
                    kwargs = service.call_args.kwargs
                    self.assertIs(kwargs["db"], db)
                    self.assertEqual(kwargs["merchant_id"], "m_demo")
                    self.assertEqual(kwargs["actor"].reason, "Ops action.")
                    if "{" not in path and service_name != "create_qr_account":
                        self.assertEqual(kwargs["qr_account_id"], qr_account_id)
        finally:
            app.dependency_overrides.clear()

    def _override_db(self, app, db) -> None:
        from app.controllers.deps import get_db

        def db_override():
            return db

        app.dependency_overrides[get_db] = db_override


def _actor_json() -> dict:
    return {
        "actor_type": "OPS",
        "actor_id": None,
        "reason": "Ops action.",
    }


def _create_merchant_json() -> dict:
    return {
        "actor": _actor_json(),
        "merchant_id": "m_demo",
        "merchant_name": "Demo Merchant",
        "legal_name": "Demo Merchant LLC",
        "contact_name": "Demo Ops",
        "contact_email": "ops@example.com",
        "contact_phone": "+84000000000",
        "webhook_url": "https://merchant.example.com/webhooks/payment-gateway",
        "settlement_account_name": "Demo Merchant LLC",
        "settlement_account_number": "123456789",
        "settlement_bank_code": "DEMO",
    }


def _submit_onboarding_json() -> dict:
    return {
        "actor": _actor_json(),
        "domain_or_app_name": "Demo Shop",
        "submitted_profile_json": {"business_type": "online_shop"},
        "documents_json": {"business_license": "demo-license.pdf"},
        "review_checks_json": {"risk_level": "LOW"},
    }


def _review_onboarding_json(note: str) -> dict:
    return {
        "actor": _actor_json(),
        "decision_note": note,
    }


def _credential_json(access_key: str) -> dict:
    return {
        "actor": _actor_json(),
        "access_key": access_key,
        "secret_key": "plain-secret",
    }


def _reason_json() -> dict:
    return {"actor": _actor_json()}


def _qr_account_json() -> dict:
    return {
        "actor": _actor_json(),
        "provider": "VIETQR",
        "bank_code": "VCB",
        "bank_bin": "970436",
        "account_number": "9704361234567890",
        "account_name": "DEMO MERCHANT LLC",
        "template": "compact",
        "status": "ACTIVE",
    }


def _qr_account_update_json() -> dict:
    return {
        "actor": _actor_json(),
        "account_name": "UPDATED DEMO MERCHANT LLC",
    }


if __name__ == "__main__":
    unittest.main()
