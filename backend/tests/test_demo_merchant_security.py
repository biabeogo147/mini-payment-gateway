import hashlib
import hmac
import json
import unittest
from datetime import datetime, timedelta, timezone


class DemoMerchantSecurityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 6, 20, 9, 30, tzinfo=timezone.utc)
        self.body = json.dumps(
            {"amount": "100000", "order_id": "ORDER-1001"},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    def test_builds_merchant_hmac_headers_for_exact_body(self) -> None:
        from demo_merchant.security import build_merchant_headers

        headers = build_merchant_headers(
            merchant_id="m_demo",
            access_key="ak_demo",
            secret="merchant-secret",
            method="POST",
            path="/v1/payments",
            body=self.body,
            now=self.now,
        )

        timestamp = "2026-06-20T09:30:00Z"
        signing_string = f"{timestamp}.POST./v1/payments.{hashlib.sha256(self.body).hexdigest()}"
        expected = hmac.new(
            b"merchant-secret",
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(headers["X-Merchant-Id"], "m_demo")
        self.assertEqual(headers["X-Access-Key"], "ak_demo")
        self.assertEqual(headers["X-Timestamp"], timestamp)
        self.assertEqual(headers["X-Signature"], expected)

    def test_builds_provider_hmac_headers_for_exact_body(self) -> None:
        from demo_merchant.security import build_provider_headers

        headers = build_provider_headers(
            provider_id="simulator",
            secret="provider-secret",
            method="POST",
            path="/v1/provider/callbacks/payment",
            body=self.body,
            now=self.now,
        )

        timestamp = "2026-06-20T09:30:00Z"
        signing_string = (
            f"{timestamp}.POST./v1/provider/callbacks/payment."
            f"{hashlib.sha256(self.body).hexdigest()}"
        )
        expected = hmac.new(
            b"provider-secret",
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(headers["X-Provider-Id"], "simulator")
        self.assertEqual(headers["X-Provider-Timestamp"], timestamp)
        self.assertEqual(headers["X-Provider-Signature"], expected)

    def test_verifies_webhook_signature_and_rejects_stale_timestamp(self) -> None:
        from demo_merchant.security import WebhookAuthError, verify_webhook_signature

        event_id = "evt_1001"
        timestamp = "2026-06-20T09:30:00Z"
        signing_string = f"{timestamp}.{event_id}.{hashlib.sha256(self.body).hexdigest()}"
        signature = hmac.new(
            b"merchant-secret",
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        verify_webhook_signature(
            secret="merchant-secret",
            event_id=event_id,
            timestamp=timestamp,
            signature=signature,
            body=self.body,
            now=self.now,
        )

        with self.assertRaises(WebhookAuthError):
            verify_webhook_signature(
                secret="merchant-secret",
                event_id=event_id,
                timestamp=timestamp,
                signature=signature,
                body=self.body,
                now=self.now + timedelta(minutes=6),
            )


if __name__ == "__main__":
    unittest.main()
