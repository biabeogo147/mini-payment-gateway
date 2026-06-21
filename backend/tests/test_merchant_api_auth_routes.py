import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.enums import CredentialStatus, MerchantStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.schemas.auth import AuthenticatedMerchant


class MerchantApiAuthRouteTest(unittest.TestCase):
    def test_verify_returns_the_authenticated_merchant(self) -> None:
        from app.controllers.deps import get_authenticated_merchant
        from app.main import app

        authenticated = AuthenticatedMerchant(
            merchant=Merchant(
                id=uuid4(),
                merchant_id="m_demo",
                merchant_name="Demo Merchant",
                contact_email="owner@example.com",
                status=MerchantStatus.ACTIVE,
            ),
            credential=MerchantCredential(
                id=uuid4(),
                merchant_db_id=uuid4(),
                access_key="ak_demo",
                secret_key_encrypted="merchant-secret",
                secret_key_last4="cret",
                status=CredentialStatus.ACTIVE,
            ),
            merchant_id="m_demo",
        )

        async def authenticated_override():
            return authenticated

        app.dependency_overrides[get_authenticated_merchant] = authenticated_override
        try:
            response = TestClient(app).get("/v1/merchant/auth/verify")
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"authenticated": True, "merchant_id": "m_demo"},
        )


if __name__ == "__main__":
    unittest.main()
