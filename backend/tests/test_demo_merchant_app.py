import hashlib
import hmac
import json
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient


class _FakeGatewayClient:
    def __init__(self) -> None:
        self.create_calls = []
        self.simulate_calls = []
        self.verify_calls = []
        self.verify_error = None

    def verify_integration(self, *, integration):
        self.verify_calls.append(integration)
        if self.verify_error is not None:
            raise self.verify_error
        return {"authenticated": True, "merchant_id": integration.merchant_id}

    def create_payment(self, *, integration, order_id, amount, description, ttl_seconds):
        self.create_calls.append(
            {
                "integration": integration,
                "order_id": order_id,
                "amount": amount,
                "description": description,
                "ttl_seconds": ttl_seconds,
            }
        )
        return {
            "transaction_id": "pay_demo_1001",
            "order_id": order_id,
            "merchant_id": integration.merchant_id,
            "qr_reference": "PDEMO1001",
            "qr_content": "0002010102123854DEMO",
            "qr_image_url": None,
            "qr_image_base64": "data:image/png;base64,UE5H",
            "status": "PENDING",
            "expire_at": "2026-06-20T09:35:00Z",
        }

    def simulate_payment_result(self, *, order, outcome):
        self.simulate_calls.append({"order": order, "outcome": outcome})
        return {
            "transaction_id": order.transaction_id,
            "status": outcome,
            "processing_result": "PROCESSED",
            "reconciliation_record_id": None,
        }


class DemoMerchantAppTest(unittest.TestCase):
    def setUp(self) -> None:
        from demo_merchant.config import DemoMerchantSettings
        from demo_merchant.main import create_app
        from demo_merchant.store import DemoOrderStore

        self.now = datetime(2026, 6, 20, 9, 30, tzinfo=timezone.utc)
        self.store = DemoOrderStore()
        self.gateway = _FakeGatewayClient()
        self.app = create_app(
            settings=DemoMerchantSettings(
                gateway_base_url="http://gateway.test",
                provider_id="simulator",
                provider_callback_secret="provider-secret",
                demo_mode=True,
            ),
            store=self.store,
            gateway_client=self.gateway,
            clock=lambda: self.now,
        )
        self.client = TestClient(self.app)

    def configure(self) -> None:
        response = self.client.put(
            "/api/setup",
            json={
                "merchant_id": "m_demo",
                "access_key": "ak_demo",
                "secret_key": "merchant-secret",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"configured": True, "merchant_id": "m_demo"})
        self.assertNotIn("secret", response.text)

    def create_order(self):
        response = self.client.post(
            "/api/orders",
            json={"amount": 100000, "description": "Thanh toan don hang", "ttl_seconds": 300},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def test_home_serves_vietnamese_checkout(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Thanh toán VietQR", response.text)
        self.assertIn("Mô phỏng ngân hàng", response.text)
        self.assertIn('id="new-order"', response.text)

    def test_health_restores_configured_merchant_without_exposing_credentials(self) -> None:
        unconfigured = self.client.get("/health")
        self.assertEqual(
            unconfigured.json(),
            {"status": "ok", "configured": False, "merchant_id": None},
        )

        self.configure()
        configured = self.client.get("/health")

        self.assertEqual(
            configured.json(),
            {"status": "ok", "configured": True, "merchant_id": "m_demo"},
        )
        self.assertNotIn("access_key", configured.text)
        self.assertNotIn("secret", configured.text)

    def test_stylesheet_keeps_hidden_checkout_states_out_of_layout(self) -> None:
        response = self.client.get("/static/styles.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn("[hidden] { display: none !important; }", response.text)

    def test_setup_does_not_return_secret_and_create_requires_setup(self) -> None:
        missing_setup = self.client.post(
            "/api/orders",
            json={"amount": 100000, "description": "Demo", "ttl_seconds": 300},
        )
        self.assertEqual(missing_setup.status_code, 409)
        self.assertEqual(missing_setup.json()["detail"], "Demo merchant is not configured.")

        self.configure()
        self.assertEqual(len(self.gateway.verify_calls), 1)
        created = self.create_order().json()

        self.assertEqual(created["status"], "PENDING")
        self.assertEqual(created["notification_state"], "WAITING_FOR_BANK")
        self.assertEqual(created["qr_reference"], "PDEMO1001")
        self.assertTrue(created["qr_image_base64"].startswith("data:image/png;base64,"))
        self.assertEqual(len(self.gateway.create_calls), 1)

    def test_setup_rejects_invalid_gateway_credential_without_persisting_it(self) -> None:
        from demo_merchant.gateway_client import GatewayClientError

        self.gateway.verify_error = GatewayClientError("Merchant authentication failed.", 401)

        response = self.client.put(
            "/api/setup",
            json={
                "merchant_id": "m_wrong",
                "access_key": "ak_wrong",
                "secret_key": "wrong-secret",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Merchant authentication failed.")
        self.assertEqual(self.client.get("/health").json()["configured"], False)

    def test_simulator_waits_for_webhook_before_terminal_status(self) -> None:
        self.configure()
        created = self.create_order().json()
        order_id = created["order_id"]

        simulated = self.client.post(
            f"/api/orders/{order_id}/simulate-result",
            json={"status": "SUCCESS"},
        )

        self.assertEqual(simulated.status_code, 200, simulated.text)
        self.assertEqual(simulated.json()["status"], "PENDING")
        self.assertEqual(simulated.json()["notification_state"], "AWAITING_WEBHOOK")
        self.assertEqual(len(self.gateway.simulate_calls), 1)

        webhook = self._send_webhook(
            event_id="evt_success",
            event_type="payment.succeeded",
            order_id=order_id,
            transaction_id="pay_demo_1001",
            status="SUCCESS",
        )
        self.assertEqual(webhook.status_code, 200, webhook.text)

        final = self.client.get(f"/api/orders/{order_id}").json()
        self.assertEqual(final["status"], "SUCCESS")
        self.assertEqual(final["notification_state"], "WEBHOOK_RECEIVED")
        self.assertEqual(final["webhook_event_id"], "evt_success")

    def test_bad_webhook_signature_is_rejected_without_state_change(self) -> None:
        self.configure()
        order_id = self.create_order().json()["order_id"]
        body = self._webhook_body(
            event_id="evt_bad",
            event_type="payment.succeeded",
            order_id=order_id,
            transaction_id="pay_demo_1001",
            status="SUCCESS",
        )

        response = self.client.post(
            "/webhooks/payment-gateway",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Event-Id": "evt_bad",
                "X-Webhook-Timestamp": "2026-06-20T09:30:00Z",
                "X-Webhook-Signature": "bad-signature",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get(f"/api/orders/{order_id}").json()["status"], "PENDING")

    def test_missing_webhook_auth_headers_are_rejected_without_state_change(self) -> None:
        self.configure()
        order_id = self.create_order().json()["order_id"]
        body = self._webhook_body(
            event_id="evt_missing_auth",
            event_type="payment.succeeded",
            order_id=order_id,
            transaction_id="pay_demo_1001",
            status="SUCCESS",
        )

        response = self.client.post(
            "/webhooks/payment-gateway",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get(f"/api/orders/{order_id}").json()["status"], "PENDING")

    def test_duplicate_webhook_is_idempotent_and_failed_reason_is_exposed(self) -> None:
        self.configure()
        order_id = self.create_order().json()["order_id"]

        first = self._send_webhook(
            event_id="evt_failed",
            event_type="payment.failed",
            order_id=order_id,
            transaction_id="pay_demo_1001",
            status="FAILED",
            failed_reason="Ngan hang tu choi giao dich.",
        )
        second = self._send_webhook(
            event_id="evt_failed",
            event_type="payment.failed",
            order_id=order_id,
            transaction_id="pay_demo_1001",
            status="FAILED",
            failed_reason="Ngan hang tu choi giao dich.",
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        final = self.client.get(f"/api/orders/{order_id}").json()
        self.assertEqual(final["status"], "FAILED")
        self.assertEqual(final["failed_reason"], "Ngan hang tu choi giao dich.")
        self.assertEqual(len(self.store.processed_event_ids), 1)

    def test_demo_reset_requires_demo_mode(self) -> None:
        self.configure()
        self.create_order()
        reset = self.client.post("/api/demo/reset")
        self.assertEqual(reset.status_code, 200)
        self.assertFalse(reset.json()["configured"])

        from demo_merchant.config import DemoMerchantSettings
        from demo_merchant.main import create_app

        disabled_app = create_app(
            settings=DemoMerchantSettings(
                gateway_base_url="http://gateway.test",
                provider_id="simulator",
                provider_callback_secret="provider-secret",
                demo_mode=False,
            ),
            gateway_client=self.gateway,
            clock=lambda: self.now,
        )
        disabled = TestClient(disabled_app).post("/api/demo/reset")
        self.assertEqual(disabled.status_code, 404)

    def _send_webhook(
        self,
        *,
        event_id: str,
        event_type: str,
        order_id: str,
        transaction_id: str,
        status: str,
        failed_reason: str | None = None,
    ):
        body = self._webhook_body(
            event_id=event_id,
            event_type=event_type,
            order_id=order_id,
            transaction_id=transaction_id,
            status=status,
            failed_reason=failed_reason,
        )
        timestamp = "2026-06-20T09:30:00Z"
        signing_string = f"{timestamp}.{event_id}.{hashlib.sha256(body).hexdigest()}"
        signature = hmac.new(
            b"merchant-secret",
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return self.client.post(
            "/webhooks/payment-gateway",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Webhook-Event-Id": event_id,
                "X-Webhook-Event-Type": event_type,
                "X-Webhook-Timestamp": timestamp,
                "X-Webhook-Signature": signature,
            },
        )

    def _webhook_body(
        self,
        *,
        event_id: str,
        event_type: str,
        order_id: str,
        transaction_id: str,
        status: str,
        failed_reason: str | None = None,
    ) -> bytes:
        return json.dumps(
            {
                "event_id": event_id,
                "event_type": event_type,
                "merchant_id": "m_demo",
                "entity_type": "PAYMENT",
                "entity_id": "00000000-0000-0000-0000-000000000001",
                "created_at": "2026-06-20T09:30:00Z",
                "data": {
                    "transaction_id": transaction_id,
                    "order_id": order_id,
                    "amount": "100000.00",
                    "currency": "VND",
                    "status": status,
                    "paid_at": "2026-06-20T09:30:00Z" if status == "SUCCESS" else None,
                    "expire_at": "2026-06-20T09:35:00Z",
                    "external_reference": "bank-demo-1001",
                    "failed_reason_code": "BANK_REJECTED" if status == "FAILED" else None,
                    "failed_reason_message": failed_reason,
                },
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
