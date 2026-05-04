import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class ExpirationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc)

    def test_overdue_pending_payments_become_expired(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.expiration_service import expire_overdue_payments

        overdue = _payment(
            transaction_id="pay_overdue",
            status=PaymentStatus.PENDING,
            expire_at=self.now - timedelta(seconds=1),
        )
        future = _payment(
            transaction_id="pay_future",
            status=PaymentStatus.PENDING,
            expire_at=self.now + timedelta(seconds=60),
        )
        store = _ExpirationStore([overdue, future], now=self.now)
        db = _FakeDb()

        with store.patched_repositories():
            expired_count = expire_overdue_payments(db, now=self.now)

        self.assertEqual(expired_count, 1)
        self.assertEqual(overdue.status, PaymentStatus.EXPIRED)
        self.assertEqual(future.status, PaymentStatus.PENDING)
        self.assertEqual(store.saved_payments, [overdue])
        self.assertTrue(db.committed)

    def test_final_state_payments_stay_unchanged_even_if_overdue(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.expiration_service import expire_overdue_payments

        success = _payment(
            transaction_id="pay_success",
            status=PaymentStatus.SUCCESS,
            expire_at=self.now - timedelta(minutes=5),
        )
        failed = _payment(
            transaction_id="pay_failed",
            status=PaymentStatus.FAILED,
            expire_at=self.now - timedelta(minutes=5),
        )
        store = _ExpirationStore([success, failed], now=self.now)

        with store.patched_repositories():
            expired_count = expire_overdue_payments(_FakeDb(), now=self.now)

        self.assertEqual(expired_count, 0)
        self.assertEqual(success.status, PaymentStatus.SUCCESS)
        self.assertEqual(failed.status, PaymentStatus.FAILED)
        self.assertEqual(store.saved_payments, [])

    def test_expiration_is_repeat_safe(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.expiration_service import expire_overdue_payments

        overdue = _payment(
            transaction_id="pay_overdue",
            status=PaymentStatus.PENDING,
            expire_at=self.now - timedelta(seconds=1),
        )
        store = _ExpirationStore([overdue], now=self.now)

        with store.patched_repositories():
            first_count = expire_overdue_payments(_FakeDb(), now=self.now)
            second_count = expire_overdue_payments(_FakeDb(), now=self.now)

        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 0)
        self.assertEqual(overdue.status, PaymentStatus.EXPIRED)


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class _ExpirationStore:
    def __init__(self, payments, now: datetime) -> None:
        self.payments = payments
        self.now = now
        self.saved_payments = []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.expiration_service.payment_repository.find_overdue_pending",
                side_effect=self.find_overdue_pending,
            ),
            patch(
                "app.services.expiration_service.payment_repository.save",
                side_effect=self.save_payment,
            ),
            patch(
                "app.services.expiration_service.webhook_event_factory.create_payment_event_if_needed",
                return_value=None,
            ),
        )

    def find_overdue_pending(self, db, now):
        from app.models.enums import PaymentStatus

        return [
            payment
            for payment in self.payments
            if payment.status == PaymentStatus.PENDING and payment.expire_at <= now
        ]

    def save_payment(self, db, payment):
        self.saved_payments.append(payment)
        return payment


class _PatchGroup:
    def __init__(self, *patches) -> None:
        self.patches = patches

    def __enter__(self):
        for patcher in self.patches:
            patcher.__enter__()

    def __exit__(self, exc_type, exc, traceback):
        for patcher in reversed(self.patches):
            patcher.__exit__(exc_type, exc, traceback)


def _payment(transaction_id: str, status, expire_at: datetime):
    from app.models.payment_transaction import PaymentTransaction

    return PaymentTransaction(
        id=uuid4(),
        transaction_id=transaction_id,
        merchant_db_id=uuid4(),
        order_reference_id=uuid4(),
        order_id=f"ORDER-{transaction_id}",
        amount=Decimal("100000.00"),
        currency="VND",
        description="Demo QR payment",
        status=status,
        qr_content="MINI_GATEWAY|...",
        expire_at=expire_at,
    )


if __name__ == "__main__":
    unittest.main()
