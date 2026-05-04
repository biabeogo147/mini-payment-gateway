import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import CredentialStatus, MerchantStatus, OnboardingCaseStatus
from app.schemas.ops import CredentialOpsResponse, MerchantOpsResponse, OnboardingCaseResponse


class MerchantOpsRouteTest(unittest.TestCase):
    def test_create_merchant_route_calls_service_with_request_db_and_actor(self) -> None:
        from app.controllers import ops_merchant_controller
        from app.main import app

        db = object()
        self._override_db(app, db)
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
            ("/v1/ops/merchants/m_demo/credentials", "create_credential", _credential_json("ak_new")),
            ("/v1/ops/merchants/m_demo/credentials/rotate", "rotate_credential", _credential_json("ak_rotated")),
        )

        try:
            for path, service_name, body in route_cases:
                with self.subTest(path=path):
                    with patch.object(
                        ops_merchant_controller.merchant_ops_service,
                        service_name,
                        return_value=response_body,
                    ) as service:
                        response = TestClient(app).post(path, json=body)

                    self.assertEqual(response.status_code, 200)
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
            ("/v1/ops/merchants/m_demo/activate", "activate_merchant", MerchantStatus.ACTIVE),
            ("/v1/ops/merchants/m_demo/suspend", "suspend_merchant", MerchantStatus.SUSPENDED),
            ("/v1/ops/merchants/m_demo/disable", "disable_merchant", MerchantStatus.DISABLED),
        )

        try:
            for path, service_name, expected_status in route_cases:
                with self.subTest(path=path):
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

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["status"], expected_status.value)
                    kwargs = service.call_args.kwargs
                    self.assertIs(kwargs["db"], db)
                    self.assertEqual(kwargs["merchant_id"], "m_demo")
                    self.assertEqual(kwargs["actor"].actor_type.value, "OPS")
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


if __name__ == "__main__":
    unittest.main()
