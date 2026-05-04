import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class WebhookRepositoryTest(unittest.TestCase):
    def test_create_event_adds_pending_event_and_flushes(self) -> None:
        from app.models.enums import EntityType, WebhookEventStatus
        from app.repositories.webhook_repository import create_event

        db = _FakeDb()
        merchant_db_id = uuid4()
        payment_id = uuid4()
        now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)

        event = create_event(
            db=db,
            event_id="evt_123",
            merchant_db_id=merchant_db_id,
            event_type="payment.succeeded",
            entity_type=EntityType.PAYMENT,
            entity_id=payment_id,
            payload_json={"event_id": "evt_123"},
            next_retry_at=now,
        )

        self.assertIs(db.added[0], event)
        self.assertTrue(db.flushed)
        self.assertEqual(event.status, WebhookEventStatus.PENDING)
        self.assertEqual(event.attempt_count, 0)
        self.assertEqual(event.next_retry_at, now)

    def test_create_delivery_attempt_adds_attempt_and_flushes(self) -> None:
        from app.models.enums import DeliveryAttemptResult
        from app.repositories.webhook_repository import create_delivery_attempt

        db = _FakeDb()
        started_at = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)

        attempt = create_delivery_attempt(
            db=db,
            webhook_event_id=uuid4(),
            attempt_no=1,
            request_url="https://merchant.example.com/webhook",
            request_headers_json={"X-Webhook-Event-Id": "evt_123"},
            request_body_json={"event_id": "evt_123"},
            response_status_code=200,
            response_body_snippet="ok",
            error_message=None,
            started_at=started_at,
            finished_at=started_at,
            result=DeliveryAttemptResult.SUCCESS,
        )

        self.assertIs(db.added[0], attempt)
        self.assertTrue(db.flushed)
        self.assertEqual(attempt.attempt_no, 1)
        self.assertEqual(attempt.request_body_json, {"event_id": "evt_123"})
        self.assertEqual(attempt.result, DeliveryAttemptResult.SUCCESS)


class WebhookEventFactoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)
        self.merchant = _merchant(webhook_url="https://merchant.example.com/webhook")
        self.payment = _payment(self.merchant.id, status="SUCCESS")
        self.payment.paid_at = self.now

    def test_payment_final_states_create_expected_event_types(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.webhook_event_factory import create_payment_event_if_needed

        cases = (
            (PaymentStatus.SUCCESS, "payment.succeeded"),
            (PaymentStatus.FAILED, "payment.failed"),
            (PaymentStatus.EXPIRED, "payment.expired"),
        )

        for status, event_type in cases:
            with self.subTest(status=status.value):
                payment = _payment(self.merchant.id, status=status)
                payment.paid_at = self.now if status == PaymentStatus.SUCCESS else None
                store = _WebhookFactoryStore(merchants=[self.merchant])

                with store.patched_repositories():
                    event = create_payment_event_if_needed(_FakeDb(), payment, now=self.now)

                self.assertIsNotNone(event)
                self.assertEqual(event.event_type, event_type)
                self.assertEqual(event.payload_json["event_type"], event_type)
                self.assertEqual(event.payload_json["merchant_id"], self.merchant.merchant_id)
                self.assertEqual(event.payload_json["data"]["transaction_id"], payment.transaction_id)
                self.assertEqual(len(store.events), 1)

    def test_refund_final_states_create_expected_event_types(self) -> None:
        from app.models.enums import RefundStatus
        from app.services.webhook_event_factory import create_refund_event_if_needed

        cases = (
            (RefundStatus.REFUNDED, "refund.succeeded"),
            (RefundStatus.REFUND_FAILED, "refund.failed"),
        )

        for status, event_type in cases:
            with self.subTest(status=status.value):
                refund = _refund(self.merchant.id, self.payment.id, status=status)
                store = _WebhookFactoryStore(merchants=[self.merchant], payments=[self.payment])

                with store.patched_repositories():
                    event = create_refund_event_if_needed(_FakeDb(), refund, now=self.now)

                self.assertIsNotNone(event)
                self.assertEqual(event.event_type, event_type)
                self.assertEqual(event.payload_json["entity_type"], "REFUND")
                self.assertEqual(event.payload_json["data"]["original_transaction_id"], self.payment.transaction_id)
                self.assertEqual(event.payload_json["data"]["refund_transaction_id"], refund.refund_transaction_id)

    def test_missing_webhook_url_does_not_create_event(self) -> None:
        from app.services.webhook_event_factory import create_payment_event_if_needed

        merchant = _merchant(webhook_url=None)
        payment = _payment(merchant.id, status="SUCCESS")
        store = _WebhookFactoryStore(merchants=[merchant])

        with store.patched_repositories():
            event = create_payment_event_if_needed(_FakeDb(), payment, now=self.now)

        self.assertIsNone(event)
        self.assertEqual(len(store.events), 0)

    def test_duplicate_event_returns_existing_event_without_insert(self) -> None:
        from app.models.enums import EntityType
        from app.models.webhook_event import WebhookEvent
        from app.services.webhook_event_factory import create_payment_event_if_needed

        existing = WebhookEvent(
            id=uuid4(),
            event_id="evt_existing",
            merchant_db_id=self.merchant.id,
            event_type="payment.succeeded",
            entity_type=EntityType.PAYMENT,
            entity_id=self.payment.id,
            payload_json={"event_id": "evt_existing"},
        )
        store = _WebhookFactoryStore(merchants=[self.merchant], events=[existing])

        with store.patched_repositories():
            event = create_payment_event_if_needed(_FakeDb(), self.payment, now=self.now)

        self.assertIs(event, existing)
        self.assertEqual(len(store.events), 1)


class _FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flushed = True


class _WebhookFactoryStore:
    def __init__(self, merchants=None, payments=None, events=None) -> None:
        self.merchants = merchants or []
        self.payments = payments or []
        self.events = events or []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.webhook_event_factory.merchant_repository.get_by_id",
                side_effect=self.get_merchant_by_id,
            ),
            patch(
                "app.services.webhook_event_factory.payment_repository.get_by_id",
                side_effect=self.get_payment_by_id,
            ),
            patch(
                "app.services.webhook_event_factory.webhook_repository.get_existing_event",
                side_effect=self.get_existing_event,
            ),
            patch(
                "app.services.webhook_event_factory.webhook_repository.create_event",
                side_effect=self.create_event,
            ),
        )

    def get_merchant_by_id(self, db, merchant_db_id):
        for merchant in self.merchants:
            if merchant.id == merchant_db_id:
                return merchant
        return None

    def get_payment_by_id(self, db, payment_id):
        for payment in self.payments:
            if payment.id == payment_id:
                return payment
        return None

    def get_existing_event(self, db, merchant_db_id, event_type, entity_type, entity_id):
        for event in self.events:
            if (
                event.merchant_db_id == merchant_db_id
                and event.event_type == event_type
                and event.entity_type == entity_type
                and event.entity_id == entity_id
            ):
                return event
        return None

    def create_event(self, db, **kwargs):
        from app.models.enums import WebhookEventStatus
        from app.models.webhook_event import WebhookEvent

        event = WebhookEvent(id=uuid4(), status=WebhookEventStatus.PENDING, attempt_count=0, **kwargs)
        self.events.append(event)
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


def _payment(merchant_db_id, status):
    from app.models.enums import PaymentStatus
    from app.models.payment_transaction import PaymentTransaction

    if isinstance(status, str):
        status = PaymentStatus(status)
    return PaymentTransaction(
        id=uuid4(),
        transaction_id="pay_123",
        merchant_db_id=merchant_db_id,
        order_reference_id=uuid4(),
        order_id="ORDER-1001",
        amount=Decimal("100000.00"),
        currency="VND",
        description="Demo QR payment",
        status=status,
        qr_content="MINI_GATEWAY|...",
        expire_at=datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc),
    )


def _refund(merchant_db_id, payment_transaction_id, status):
    from app.models.enums import RefundStatus
    from app.models.refund_transaction import RefundTransaction

    if isinstance(status, str):
        status = RefundStatus(status)
    return RefundTransaction(
        id=uuid4(),
        refund_transaction_id="rfnd_123",
        merchant_db_id=merchant_db_id,
        payment_transaction_id=payment_transaction_id,
        refund_id="REF-1001",
        refund_amount=Decimal("100000.00"),
        reason="Customer requested refund",
        status=status,
        processed_at=datetime(2026, 4, 29, 10, 10, tzinfo=timezone.utc),
    )


if __name__ == "__main__":
    unittest.main()
