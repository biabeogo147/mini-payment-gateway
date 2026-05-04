import hashlib
import hmac
import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import uuid4

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import CredentialStatus, MerchantStatus
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.payment_transaction import PaymentTransaction
from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.models.webhook_event import WebhookEvent
from app.services.webhook_delivery_service import deliver_event
from smoke_payment_api import create_payment, free_port, wait_for_health
from smoke_provider_callback_api import send_success_callback


def main() -> None:
    receiver = WebhookReceiver()
    receiver.start()
    seed = seed_merchant(webhook_url=receiver.url)
    api_port = free_port()
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_health(api_port, process)
        created = create_payment(api_port, seed)
        callback = send_success_callback(api_port, created)
        event_state_before = get_payment_webhook_state(created["transaction_id"])
        deliver_payment_webhook(created["transaction_id"])
        delivered_request = receiver.wait_for_request()
        event_state_after = get_payment_webhook_state(created["transaction_id"])
        signature_valid = verify_webhook_signature(
            request=delivered_request,
            secret=seed["secret"],
        )
        print(
            json.dumps(
                {
                    "api_port": api_port,
                    "receiver_port": receiver.port,
                    "merchant_id": seed["merchant_id"],
                    "transaction_id": created["transaction_id"],
                    "callback_processing_result": callback["processing_result"],
                    "event_type": event_state_after["event_type"],
                    "event_status_before_delivery": event_state_before["event_status"],
                    "event_status_after_delivery": event_state_after["event_status"],
                    "attempt_result": event_state_after["attempt_result"],
                    "attempt_count": event_state_after["attempt_count"],
                    "delivery_invoked": True,
                    "receiver_request_count": len(receiver.requests),
                    "signature_valid": signature_valid,
                },
                sort_keys=True,
            )
        )
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        receiver.stop()


def seed_merchant(webhook_url: str) -> dict[str, str]:
    suffix = uuid4().hex[:8]
    merchant_id = f"m_phase6_{suffix}"
    access_key = f"ak_phase6_{suffix}"
    secret = f"phase6-secret-{suffix}"
    with SessionLocal() as db:
        merchant = Merchant(
            merchant_id=merchant_id,
            merchant_name="Phase 6 Smoke Merchant",
            contact_email=f"phase6-{suffix}@example.com",
            webhook_url=webhook_url,
            status=MerchantStatus.ACTIVE,
        )
        db.add(merchant)
        db.flush()
        credential = MerchantCredential(
            merchant_db_id=merchant.id,
            access_key=access_key,
            secret_key_encrypted=secret,
            secret_key_last4=secret[-4:],
            status=CredentialStatus.ACTIVE,
        )
        db.add(credential)
        db.commit()
    return {
        "merchant_id": merchant_id,
        "access_key": access_key,
        "secret": secret,
        "order_id": f"ORDER-PHASE6-{suffix}",
    }


def deliver_payment_webhook(transaction_id: str) -> None:
    with SessionLocal() as db:
        payment = db.scalar(select(PaymentTransaction).where(PaymentTransaction.transaction_id == transaction_id))
        if payment is None:
            raise RuntimeError(f"Payment row not found: {transaction_id}")
        event = db.scalar(
            select(WebhookEvent)
            .where(
                WebhookEvent.entity_id == payment.id,
                WebhookEvent.event_type == "payment.succeeded",
            )
            .order_by(WebhookEvent.created_at.desc())
            .limit(1)
        )
        if event is None:
            raise RuntimeError(f"Webhook event not found for payment: {transaction_id}")
        deliver_event(db, event)


def get_payment_webhook_state(transaction_id: str) -> dict[str, str | int | None]:
    with SessionLocal() as db:
        payment = db.scalar(select(PaymentTransaction).where(PaymentTransaction.transaction_id == transaction_id))
        if payment is None:
            raise RuntimeError(f"Payment row not found: {transaction_id}")

        event = db.scalar(
            select(WebhookEvent)
            .where(
                WebhookEvent.entity_id == payment.id,
                WebhookEvent.event_type == "payment.succeeded",
            )
            .order_by(WebhookEvent.created_at.desc())
            .limit(1)
        )
        if event is None:
            raise RuntimeError(f"Webhook event not found for payment: {transaction_id}")

        attempt = db.scalar(
            select(WebhookDeliveryAttempt)
            .where(WebhookDeliveryAttempt.webhook_event_id == event.id)
            .order_by(WebhookDeliveryAttempt.attempt_no.desc())
            .limit(1)
        )
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_status": event.status.value,
            "attempt_count": event.attempt_count,
            "attempt_result": attempt.result.value if attempt is not None else None,
        }


def verify_webhook_signature(request: dict, secret: str) -> bool:
    headers = request["headers"]
    body = request["body"]
    timestamp = headers["X-Webhook-Timestamp"]
    event_id = headers["X-Webhook-Event-Id"]
    body_hash = hashlib.sha256(body).hexdigest()
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{timestamp}.{event_id}.{body_hash}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(headers["X-Webhook-Signature"], expected)


class WebhookReceiver:
    def __init__(self) -> None:
        self.requests = []
        self._ready = threading.Event()
        self._request_received = threading.Event()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_class())
        self.port = int(self._server.server_address[1])
        self.url = f"http://127.0.0.1:{self.port}/merchant-webhook"
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self) -> None:
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise TimeoutError("Webhook receiver did not start.")

    def stop(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)
        self._server.server_close()

    def wait_for_request(self) -> dict:
        if not self._request_received.wait(timeout=10):
            raise TimeoutError("Webhook receiver did not receive a request.")
        return self.requests[-1]

    def _serve(self) -> None:
        self._ready.set()
        self._server.serve_forever()

    def _handler_class(self):
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                receiver.requests.append(
                    {
                        "path": self.path,
                        "headers": dict(self.headers),
                        "body": body,
                    }
                )
                receiver._request_received.set()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')

            def log_message(self, format: str, *args) -> None:
                return None

        return Handler


if __name__ == "__main__":
    main()
