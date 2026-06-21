import hashlib
import hmac
import unittest

import httpx


class DemoMerchantGatewayClientTest(unittest.TestCase):
    def test_verify_integration_sends_a_signed_get_request(self) -> None:
        from demo_merchant.config import DemoMerchantSettings
        from demo_merchant.gateway_client import GatewayClient
        from demo_merchant.store import MerchantIntegration

        captured = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(
                200,
                json={"authenticated": True, "merchant_id": "m_demo"},
            )

        http_client = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(http_client.close)
        client = GatewayClient(
            DemoMerchantSettings(gateway_base_url="http://gateway.test"),
            http_client=http_client,
        )
        integration = MerchantIntegration(
            merchant_id="m_demo",
            access_key="ak_demo",
            secret_key="merchant-secret",
        )

        self.assertTrue(
            hasattr(client, "verify_integration"),
            "GatewayClient must expose credential verification.",
        )
        result = client.verify_integration(integration=integration)

        self.assertEqual(result, {"authenticated": True, "merchant_id": "m_demo"})
        self.assertEqual(len(captured), 1)
        request = captured[0]
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.path, "/v1/merchant/auth/verify")
        timestamp = request.headers["X-Timestamp"]
        signing_string = (
            f"{timestamp}.GET./v1/merchant/auth/verify."
            f"{hashlib.sha256(b'').hexdigest()}"
        )
        expected_signature = hmac.new(
            b"merchant-secret",
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(request.headers["X-Merchant-Id"], "m_demo")
        self.assertEqual(request.headers["X-Access-Key"], "ak_demo")
        self.assertEqual(request.headers["X-Signature"], expected_signature)


if __name__ == "__main__":
    unittest.main()
