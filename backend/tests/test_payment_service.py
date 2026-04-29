import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class PaymentSchemaTest(unittest.TestCase):
    def test_create_payment_request_accepts_ttl_or_expire_at(self) -> None:
        from app.schemas.payment import CreatePaymentRequest

        ttl_request = CreatePaymentRequest(
            order_id="ORDER-1001",
            amount="100000.00",
            description="Demo QR payment",
            ttl_seconds=900,
            metadata={"customer_ref": "CUST-1"},
        )
        expire_request = CreatePaymentRequest(
            order_id="ORDER-1002",
            amount=Decimal("50000.00"),
            description="Demo QR payment",
            expire_at=datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc),
        )

        self.assertEqual(ttl_request.amount, Decimal("100000.00"))
        self.assertEqual(ttl_request.currency, "VND")
        self.assertEqual(ttl_request.metadata, {"customer_ref": "CUST-1"})
        self.assertEqual(expire_request.expire_at, datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc))

    def test_create_payment_request_requires_exactly_one_expiration_strategy(self) -> None:
        from pydantic import ValidationError

        from app.schemas.payment import CreatePaymentRequest

        with self.assertRaises(ValidationError):
            CreatePaymentRequest(
                order_id="ORDER-1001",
                amount="100000.00",
                description="Demo QR payment",
            )

        with self.assertRaises(ValidationError):
            CreatePaymentRequest(
                order_id="ORDER-1001",
                amount="100000.00",
                description="Demo QR payment",
                ttl_seconds=900,
                expire_at=datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc),
            )

    def test_payment_response_can_be_built_from_payment_model(self) -> None:
        from app.models.enums import PaymentStatus
        from app.models.payment_transaction import PaymentTransaction
        from app.schemas.payment import PaymentResponse

        expire_at = datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc)
        payment = PaymentTransaction(
            id=uuid4(),
            transaction_id="pay_123",
            merchant_db_id=uuid4(),
            order_reference_id=uuid4(),
            order_id="ORDER-1001",
            amount=Decimal("100000.00"),
            currency="VND",
            description="Demo QR payment",
            status=PaymentStatus.PENDING,
            qr_content="MINI_GATEWAY|...",
            expire_at=expire_at,
        )

        response = PaymentResponse.from_payment(payment, merchant_id="m_demo")

        self.assertEqual(response.transaction_id, "pay_123")
        self.assertEqual(response.order_id, "ORDER-1001")
        self.assertEqual(response.merchant_id, "m_demo")
        self.assertEqual(response.qr_content, "MINI_GATEWAY|...")
        self.assertEqual(response.status, PaymentStatus.PENDING)
        self.assertEqual(response.expire_at, expire_at)


class QrServiceTest(unittest.TestCase):
    def test_qr_content_contains_payment_identity_and_amount(self) -> None:
        from app.services.qr_service import generate_qr_content

        qr_content = generate_qr_content(
            merchant_id="m_demo",
            transaction_id="pay_123",
            amount=Decimal("100000.00"),
            currency="VND",
        )

        self.assertEqual(
            qr_content,
            "MINI_GATEWAY|merchant_id=m_demo|transaction_id=pay_123|amount=100000.00|currency=VND",
        )

    def test_create_payment_request_resolves_expire_at_from_ttl(self) -> None:
        from app.schemas.payment import CreatePaymentRequest

        now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        request = CreatePaymentRequest(
            order_id="ORDER-1001",
            amount="100000.00",
            description="Demo QR payment",
            ttl_seconds=900,
        )

        self.assertEqual(request.resolve_expire_at(now), now + timedelta(seconds=900))


class PaymentRepositoryTest(unittest.TestCase):
    def test_order_reference_create_adds_model_and_flushes(self) -> None:
        from app.repositories.order_reference_repository import create

        db = _FakeDb()
        merchant_db_id = uuid4()

        order_reference = create(db, merchant_db_id=merchant_db_id, order_id="ORDER-1001")

        self.assertIs(db.added[0], order_reference)
        self.assertTrue(db.flushed)
        self.assertEqual(order_reference.merchant_db_id, merchant_db_id)
        self.assertEqual(order_reference.order_id, "ORDER-1001")

    def test_payment_create_adds_pending_payment_and_flushes(self) -> None:
        from app.models.enums import PaymentStatus
        from app.repositories.payment_repository import create

        db = _FakeDb()
        merchant_db_id = uuid4()
        order_reference_id = uuid4()
        expire_at = datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc)

        payment = create(
            db,
            transaction_id="pay_123",
            merchant_db_id=merchant_db_id,
            order_reference_id=order_reference_id,
            order_id="ORDER-1001",
            amount=Decimal("100000.00"),
            currency="VND",
            description="Demo QR payment",
            qr_content="MINI_GATEWAY|...",
            expire_at=expire_at,
            idempotency_key="idem-1",
        )

        self.assertIs(db.added[0], payment)
        self.assertTrue(db.flushed)
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.transaction_id, "pay_123")
        self.assertEqual(payment.idempotency_key, "idem-1")


class PaymentServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.models.enums import CredentialStatus, MerchantStatus
        from app.models.merchant import Merchant
        from app.models.merchant_credential import MerchantCredential
        from app.schemas.auth import AuthenticatedMerchant
        from app.schemas.payment import CreatePaymentRequest

        self.now = datetime(2026, 4, 29, 10, 0, tzinfo=timezone.utc)
        self.merchant = Merchant(
            id=uuid4(),
            merchant_id="m_demo",
            merchant_name="Demo Merchant",
            contact_email="ops@example.com",
            status=MerchantStatus.ACTIVE,
        )
        self.credential = MerchantCredential(
            id=uuid4(),
            merchant_db_id=self.merchant.id,
            access_key="ak_demo",
            secret_key_encrypted="super-secret",
            secret_key_last4="cret",
            status=CredentialStatus.ACTIVE,
        )
        self.authenticated = AuthenticatedMerchant(
            merchant=self.merchant,
            credential=self.credential,
            merchant_id="m_demo",
        )
        self.request = CreatePaymentRequest(
            order_id="ORDER-1001",
            amount="100000.00",
            description="Demo QR payment",
            ttl_seconds=900,
        )

    def test_create_payment_creates_order_reference_and_pending_transaction(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.payment_service import create_payment

        db = _FakeDb()
        store = _PaymentStore()

        with store.patched_repositories():
            response = create_payment(
                db=db,
                authenticated_merchant=self.authenticated,
                request=self.request,
                idempotency_key="idem-1",
                now=self.now,
            )

        self.assertTrue(db.committed)
        self.assertEqual(len(store.order_references), 1)
        self.assertEqual(len(store.payments), 1)
        payment = store.payments[0]
        order_reference = next(iter(store.order_references.values()))
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(order_reference.latest_payment_transaction_id, payment.id)
        self.assertEqual(response.transaction_id, payment.transaction_id)
        self.assertEqual(response.qr_content, payment.qr_content)
        self.assertIn("merchant_id=m_demo", response.qr_content)

    def test_duplicate_pending_semantically_identical_returns_existing_transaction(self) -> None:
        from app.services.payment_service import create_payment

        db = _FakeDb()
        store = _PaymentStore()

        with store.patched_repositories():
            first = create_payment(db, self.authenticated, self.request, "idem-1", now=self.now)
            second = create_payment(db, self.authenticated, self.request, "idem-2", now=self.now)

        self.assertEqual(first.transaction_id, second.transaction_id)
        self.assertEqual(len(store.payments), 1)

    def test_duplicate_pending_with_different_amount_rejects(self) -> None:
        from app.core.errors import AppError
        from app.schemas.payment import CreatePaymentRequest
        from app.services.payment_service import create_payment

        db = _FakeDb()
        store = _PaymentStore()
        changed_request = CreatePaymentRequest(
            order_id="ORDER-1001",
            amount="200000.00",
            description="Demo QR payment",
            ttl_seconds=900,
        )

        with store.patched_repositories():
            create_payment(db, self.authenticated, self.request, "idem-1", now=self.now)
            with self.assertRaises(AppError) as error:
                create_payment(db, self.authenticated, changed_request, "idem-2", now=self.now)

        self.assertEqual(error.exception.error_code, "PAYMENT_PENDING_EXISTS")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(store.payments), 1)

    def test_previous_failed_or_expired_payment_allows_new_attempt(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.payment_service import create_payment

        for terminal_status in (PaymentStatus.FAILED, PaymentStatus.EXPIRED):
            with self.subTest(status=terminal_status.value):
                db = _FakeDb()
                store = _PaymentStore()
                with store.patched_repositories():
                    first = create_payment(db, self.authenticated, self.request, "idem-1", now=self.now)
                    store.payments[0].status = terminal_status
                    second = create_payment(db, self.authenticated, self.request, "idem-2", now=self.now)

                self.assertNotEqual(first.transaction_id, second.transaction_id)
                self.assertEqual(len(store.payments), 2)

    def test_previous_success_payment_rejects_new_attempt(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import PaymentStatus
        from app.services.payment_service import create_payment

        db = _FakeDb()
        store = _PaymentStore()

        with store.patched_repositories():
            create_payment(db, self.authenticated, self.request, "idem-1", now=self.now)
            store.payments[0].status = PaymentStatus.SUCCESS
            with self.assertRaises(AppError) as error:
                create_payment(db, self.authenticated, self.request, "idem-2", now=self.now)

        self.assertEqual(error.exception.error_code, "PAYMENT_ALREADY_SUCCESS")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(store.payments), 1)

    def test_query_by_transaction_id_and_order_id_returns_owned_payment(self) -> None:
        from app.services.payment_service import (
            create_payment,
            get_payment_by_order_id,
            get_payment_by_transaction_id,
        )

        db = _FakeDb()
        store = _PaymentStore()

        with store.patched_repositories():
            created = create_payment(db, self.authenticated, self.request, "idem-1", now=self.now)
            by_transaction = get_payment_by_transaction_id(db, self.authenticated, created.transaction_id)
            by_order = get_payment_by_order_id(db, self.authenticated, "ORDER-1001")

        self.assertEqual(by_transaction.transaction_id, created.transaction_id)
        self.assertEqual(by_order.transaction_id, created.transaction_id)

    def test_query_foreign_transaction_returns_not_found(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import PaymentStatus
        from app.models.payment_transaction import PaymentTransaction
        from app.services.payment_service import get_payment_by_transaction_id

        db = _FakeDb()
        store = _PaymentStore()
        store.payments.append(
            PaymentTransaction(
                id=uuid4(),
                transaction_id="pay_foreign",
                merchant_db_id=uuid4(),
                order_reference_id=uuid4(),
                order_id="ORDER-FOREIGN",
                amount=Decimal("100000.00"),
                currency="VND",
                description="Foreign payment",
                status=PaymentStatus.PENDING,
                qr_content="MINI_GATEWAY|...",
                expire_at=self.now + timedelta(seconds=900),
            )
        )

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                get_payment_by_transaction_id(db, self.authenticated, "pay_foreign")

        self.assertEqual(error.exception.error_code, "PAYMENT_NOT_FOUND")
        self.assertEqual(error.exception.status_code, 404)


class _FakeDb:
    def __init__(self) -> None:
        self.added = []
        self.flushed = False
        self.committed = False

    def add(self, item) -> None:
        self.added.append(item)

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.committed = True


class _PaymentStore:
    def __init__(self) -> None:
        self.order_references = {}
        self.payments = []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.payment_service.order_reference_repository.get_by_merchant_and_order",
                side_effect=self.get_order_reference,
            ),
            patch(
                "app.services.payment_service.order_reference_repository.create",
                side_effect=self.create_order_reference,
            ),
            patch(
                "app.services.payment_service.order_reference_repository.set_latest_payment",
                side_effect=self.set_latest_payment,
            ),
            patch(
                "app.services.payment_service.payment_repository.get_pending_by_merchant_order",
                side_effect=self.get_pending_payment,
            ),
            patch(
                "app.services.payment_service.payment_repository.get_latest_by_merchant_order",
                side_effect=self.get_latest_payment,
            ),
            patch(
                "app.services.payment_service.payment_repository.get_by_transaction_id",
                side_effect=self.get_payment_by_transaction_id,
            ),
            patch(
                "app.services.payment_service.payment_repository.create",
                side_effect=self.create_payment,
            ),
        )

    def get_order_reference(self, db, merchant_db_id, order_id):
        return self.order_references.get((merchant_db_id, order_id))

    def create_order_reference(self, db, merchant_db_id, order_id):
        from app.models.order_reference import OrderReference

        order_reference = OrderReference(
            id=uuid4(),
            merchant_db_id=merchant_db_id,
            order_id=order_id,
        )
        self.order_references[(merchant_db_id, order_id)] = order_reference
        return order_reference

    def set_latest_payment(self, db, order_reference, payment_transaction_id):
        order_reference.latest_payment_transaction_id = payment_transaction_id
        return order_reference

    def get_pending_payment(self, db, merchant_db_id, order_id):
        from app.models.enums import PaymentStatus

        for payment in reversed(self.payments):
            if payment.merchant_db_id == merchant_db_id and payment.order_id == order_id and payment.status == PaymentStatus.PENDING:
                return payment
        return None

    def get_latest_payment(self, db, merchant_db_id, order_id):
        for payment in reversed(self.payments):
            if payment.merchant_db_id == merchant_db_id and payment.order_id == order_id:
                return payment
        return None

    def get_payment_by_transaction_id(self, db, transaction_id):
        for payment in self.payments:
            if payment.transaction_id == transaction_id:
                return payment
        return None

    def create_payment(self, db, **kwargs):
        from app.models.enums import PaymentStatus
        from app.models.payment_transaction import PaymentTransaction

        payment = PaymentTransaction(
            id=uuid4(),
            status=PaymentStatus.PENDING,
            **kwargs,
        )
        self.payments.append(payment)
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


if __name__ == "__main__":
    unittest.main()
