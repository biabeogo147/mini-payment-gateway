import hashlib
import hmac
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4


class WebhookDeliveryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        self.merchant = _merchant(webhook_url="https://merchant.example.com/webhook")
        self.credential = _credential(self.merchant.id, secret="webhook-secret")
        self.event = _event(self.merchant.id, attempt_count=0)

    def test_http_2xx_marks_event_delivered_and_records_success_attempt(self) -> None:
        from app.models.enums import DeliveryAttemptResult, WebhookEventStatus
        from app.services.webhook_delivery_service import deliver_event

        store = _WebhookDeliveryStore(merchants=[self.merchant], credentials=[self.credential])
        http_client = _FakeHttpClient(responses=[_FakeResponse(200, "ok")])

        with store.patched_repositories():
            result = deliver_event(_FakeDb(), self.event, now=self.now, http_client=http_client)

        self.assertEqual(self.event.status, WebhookEventStatus.DELIVERED)
        self.assertEqual(self.event.attempt_count, 1)
        self.assertIsNone(self.event.next_retry_at)
        self.assertEqual(store.attempts[0].result, DeliveryAttemptResult.SUCCESS)
        self.assertEqual(store.attempts[0].attempt_no, 1)
        self.assertEqual(result.last_attempt_result, DeliveryAttemptResult.SUCCESS)
        self.assert_signed_request(http_client.requests[0], self.event.event_id, "webhook-secret")

    def test_http_500_schedules_retry_then_exhausts_on_attempt_4(self) -> None:
        from app.models.enums import DeliveryAttemptResult, WebhookEventStatus
        from app.services.webhook_delivery_service import deliver_event

        cases = (
            (0, self.now + timedelta(minutes=1), WebhookEventStatus.PENDING),
            (1, self.now + timedelta(minutes=5), WebhookEventStatus.PENDING),
            (2, self.now + timedelta(minutes=15), WebhookEventStatus.PENDING),
            (3, None, WebhookEventStatus.FAILED),
        )

        for attempt_count, expected_next_retry, expected_status in cases:
            with self.subTest(attempt_count=attempt_count):
                event = _event(self.merchant.id, attempt_count=attempt_count)
                store = _WebhookDeliveryStore(merchants=[self.merchant], credentials=[self.credential])
                http_client = _FakeHttpClient(responses=[_FakeResponse(500, "server error")])

                with store.patched_repositories():
                    deliver_event(_FakeDb(), event, now=self.now, http_client=http_client)

                self.assertEqual(event.status, expected_status)
                self.assertEqual(event.next_retry_at, expected_next_retry)
                self.assertEqual(event.attempt_count, attempt_count + 1)
                self.assertEqual(store.attempts[0].result, DeliveryAttemptResult.FAILED)
                self.assertEqual(store.attempts[0].response_status_code, 500)

    def test_timeout_and_network_error_record_specific_results(self) -> None:
        import httpx

        from app.models.enums import DeliveryAttemptResult
        from app.services.webhook_delivery_service import deliver_event

        cases = (
            (httpx.TimeoutException("timed out"), DeliveryAttemptResult.TIMEOUT),
            (httpx.RequestError("network failed"), DeliveryAttemptResult.NETWORK_ERROR),
        )

        for exception, expected_result in cases:
            with self.subTest(expected_result=expected_result.value):
                event = _event(self.merchant.id, attempt_count=0)
                store = _WebhookDeliveryStore(merchants=[self.merchant], credentials=[self.credential])
                http_client = _FakeHttpClient(exceptions=[exception])

                with store.patched_repositories():
                    deliver_event(_FakeDb(), event, now=self.now, http_client=http_client)

                self.assertEqual(store.attempts[0].result, expected_result)
                self.assertEqual(event.next_retry_at, self.now + timedelta(minutes=1))

    def test_missing_active_credential_marks_event_failed(self) -> None:
        from app.models.enums import WebhookEventStatus
        from app.services.webhook_delivery_service import deliver_event

        store = _WebhookDeliveryStore(merchants=[self.merchant], credentials=[])

        with store.patched_repositories():
            result = deliver_event(_FakeDb(), self.event, now=self.now, http_client=_FakeHttpClient())

        self.assertEqual(self.event.status, WebhookEventStatus.FAILED)
        self.assertEqual(result.status, WebhookEventStatus.FAILED)

    def test_deliver_due_webhooks_delivers_only_due_pending_events(self) -> None:
        from app.models.enums import WebhookEventStatus
        from app.services.webhook_delivery_service import deliver_due_webhooks

        due = _event(self.merchant.id, event_id="evt_due", next_retry_at=self.now)
        future = _event(self.merchant.id, event_id="evt_future", next_retry_at=self.now + timedelta(minutes=1))
        delivered = _event(self.merchant.id, event_id="evt_delivered", next_retry_at=self.now)
        delivered.status = WebhookEventStatus.DELIVERED
        store = _WebhookDeliveryStore(
            merchants=[self.merchant],
            credentials=[self.credential],
            events=[due, future, delivered],
        )
        http_client = _FakeHttpClient(responses=[_FakeResponse(200, "ok")])

        with store.patched_repositories():
            count = deliver_due_webhooks(_FakeDb(), now=self.now, limit=100, http_client=http_client)

        self.assertEqual(count, 1)
        self.assertEqual(due.status, WebhookEventStatus.DELIVERED)
        self.assertEqual(future.status, WebhookEventStatus.PENDING)
        self.assertEqual(delivered.status, WebhookEventStatus.DELIVERED)

    def test_manual_retry_rejects_missing_or_not_failed_event(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import WebhookEventStatus
        from app.services.webhook_delivery_service import manual_retry

        delivered = _event(self.merchant.id, event_id="evt_delivered")
        delivered.status = WebhookEventStatus.DELIVERED
        store = _WebhookDeliveryStore(events=[delivered])

        with store.patched_repositories():
            with self.assertRaises(AppError) as missing_error:
                manual_retry(_FakeDb(), "evt_missing", now=self.now, http_client=_FakeHttpClient())
            with self.assertRaises(AppError) as delivered_error:
                manual_retry(_FakeDb(), "evt_delivered", now=self.now, http_client=_FakeHttpClient())

        self.assertEqual(missing_error.exception.error_code, "WEBHOOK_EVENT_NOT_FOUND")
        self.assertEqual(delivered_error.exception.error_code, "WEBHOOK_RETRY_NOT_ALLOWED")

    def test_manual_retry_can_deliver_failed_event(self) -> None:
        from app.models.enums import WebhookEventStatus
        from app.services.webhook_delivery_service import manual_retry

        failed = _event(self.merchant.id, event_id="evt_failed", attempt_count=4)
        failed.status = WebhookEventStatus.FAILED
        store = _WebhookDeliveryStore(
            merchants=[self.merchant],
            credentials=[self.credential],
            events=[failed],
        )

        with store.patched_repositories():
            result = manual_retry(_FakeDb(), "evt_failed", now=self.now, http_client=_FakeHttpClient([_FakeResponse(200, "ok")]))

        self.assertEqual(failed.status, WebhookEventStatus.DELIVERED)
        self.assertEqual(failed.attempt_count, 5)
        self.assertEqual(result.status, WebhookEventStatus.DELIVERED)

    def assert_signed_request(self, request, event_id: str, secret: str) -> None:
        headers = request["headers"]
        body = request["content"]
        timestamp = headers["X-Webhook-Timestamp"]
        body_hash = hashlib.sha256(body).hexdigest()
        expected = hmac.new(
            secret.encode("utf-8"),
            f"{timestamp}.{event_id}.{body_hash}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        self.assertEqual(headers["X-Webhook-Event-Id"], event_id)
        self.assertEqual(headers["X-Webhook-Signature"], expected)


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class _WebhookDeliveryStore:
    def __init__(self, merchants=None, credentials=None, events=None) -> None:
        self.merchants = merchants or []
        self.credentials = credentials or []
        self.events = events or []
        self.attempts = []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.webhook_delivery_service.merchant_repository.get_by_id",
                side_effect=self.get_merchant_by_id,
            ),
            patch(
                "app.services.webhook_delivery_service.credential_repository.get_active_by_merchant",
                side_effect=self.get_active_credential,
            ),
            patch(
                "app.services.webhook_delivery_service.webhook_repository.get_by_event_id",
                side_effect=self.get_event_by_event_id,
            ),
            patch(
                "app.services.webhook_delivery_service.webhook_repository.find_due_events",
                side_effect=self.find_due_events,
            ),
            patch(
                "app.services.webhook_delivery_service.webhook_repository.create_delivery_attempt",
                side_effect=self.create_delivery_attempt,
            ),
            patch(
                "app.services.webhook_delivery_service.webhook_repository.save_event",
                side_effect=self.save_event,
            ),
        )

    def get_merchant_by_id(self, db, merchant_db_id):
        for merchant in self.merchants:
            if merchant.id == merchant_db_id:
                return merchant
        return None

    def get_active_credential(self, db, merchant_db_id):
        for credential in self.credentials:
            if credential.merchant_db_id == merchant_db_id:
                return credential
        return None

    def get_event_by_event_id(self, db, event_id):
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def find_due_events(self, db, now, limit=100):
        from app.models.enums import WebhookEventStatus

        due = [
            event
            for event in self.events
            if event.status == WebhookEventStatus.PENDING
            and event.next_retry_at is not None
            and event.next_retry_at <= now
        ]
        return due[:limit]

    def create_delivery_attempt(self, db, **kwargs):
        from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt

        attempt = WebhookDeliveryAttempt(id=uuid4(), **kwargs)
        self.attempts.append(attempt)
        return attempt

    def save_event(self, db, event):
        return event


class _PatchGroup:
    def __init__(self, *patches) -> None:
        self.patches = patches

    def __enter__(self):
        for patcher in self.patches:
            patcher.__enter__()

    def __exit__(self, exc_type, exc, traceback):
        for patcher in reversed(self.patches):
            patcher.__exit__(exc_type, exc, traceback)


class _FakeHttpClient:
    def __init__(self, responses=None, exceptions=None) -> None:
        self.responses = responses or []
        self.exceptions = exceptions or []
        self.requests = []

    def post(self, url, content, headers, timeout):
        self.requests.append({"url": url, "content": content, "headers": headers, "timeout": timeout})
        if self.exceptions:
            raise self.exceptions.pop(0)
        return self.responses.pop(0)


class _FakeResponse:
    def __init__(self, status_code, text) -> None:
        self.status_code = status_code
        self.text = text


def _merchant(webhook_url):
    from app.models.enums import MerchantStatus
    from app.models.merchant import Merchant

    return Merchant(
        id=uuid4(),
        merchant_id="m_demo",
        merchant_name="Demo Merchant",
        contact_email="ops@example.com",
        webhook_url=webhook_url,
        status=MerchantStatus.ACTIVE,
    )


def _credential(merchant_db_id, secret):
    from app.models.enums import CredentialStatus
    from app.models.merchant_credential import MerchantCredential

    return MerchantCredential(
        id=uuid4(),
        merchant_db_id=merchant_db_id,
        access_key="ak_demo",
        secret_key_encrypted=secret,
        secret_key_last4=secret[-4:],
        status=CredentialStatus.ACTIVE,
    )


def _event(merchant_db_id, event_id="evt_123", attempt_count=0, next_retry_at=None):
    from app.models.enums import EntityType, WebhookEventStatus
    from app.models.webhook_event import WebhookEvent

    payload = {
        "event_id": event_id,
        "event_type": "payment.succeeded",
        "merchant_id": "m_demo",
        "entity_type": "PAYMENT",
        "entity_id": str(uuid4()),
        "created_at": "2026-04-29T10:00:00+00:00",
        "data": {"transaction_id": "pay_123"},
    }
    return WebhookEvent(
        id=uuid4(),
        event_id=event_id,
        merchant_db_id=merchant_db_id,
        event_type="payment.succeeded",
        entity_type=EntityType.PAYMENT,
        entity_id=uuid4(),
        payload_json=payload,
        status=WebhookEventStatus.PENDING,
        attempt_count=attempt_count,
        next_retry_at=next_retry_at,
    )


if __name__ == "__main__":
    unittest.main()
