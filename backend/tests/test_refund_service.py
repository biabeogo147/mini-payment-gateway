import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class RefundSchemaTest(unittest.TestCase):
    def test_create_refund_request_accepts_exactly_one_payment_selector(self) -> None:
        from pydantic import ValidationError

        from app.schemas.refund import CreateRefundRequest

        by_transaction = CreateRefundRequest(
            original_transaction_id="pay_123",
            refund_id="REF-1001",
            refund_amount="100000.00",
            reason="Customer requested refund",
        )
        by_order = CreateRefundRequest(
            order_id="ORDER-1001",
            refund_id="REF-1002",
            refund_amount=Decimal("100000.00"),
            reason="Customer requested refund",
        )

        self.assertEqual(by_transaction.original_transaction_id, "pay_123")
        self.assertIsNone(by_transaction.order_id)
        self.assertEqual(by_order.order_id, "ORDER-1001")
        self.assertEqual(by_order.refund_amount, Decimal("100000.00"))

        with self.assertRaises(ValidationError):
            CreateRefundRequest(
                original_transaction_id="pay_123",
                order_id="ORDER-1001",
                refund_id="REF-1003",
                refund_amount="100000.00",
                reason="Customer requested refund",
            )

        with self.assertRaises(ValidationError):
            CreateRefundRequest(
                refund_id="REF-1004",
                refund_amount="100000.00",
                reason="Customer requested refund",
            )

    def test_refund_response_can_be_built_from_models(self) -> None:
        from app.models.enums import RefundStatus
        from app.schemas.refund import RefundResponse

        payment = _payment(status="SUCCESS", paid_at=datetime(2026, 4, 29, 10, tzinfo=timezone.utc))
        refund = _refund(payment=payment, status=RefundStatus.REFUND_PENDING)

        response = RefundResponse.from_refund(refund, payment)

        self.assertEqual(response.refund_transaction_id, "rfnd_123")
        self.assertEqual(response.original_transaction_id, "pay_123")
        self.assertEqual(response.refund_id, "REF-1001")
        self.assertEqual(response.refund_amount, Decimal("100000.00"))
        self.assertEqual(response.refund_status, RefundStatus.REFUND_PENDING)


class RefundRepositoryTest(unittest.TestCase):
    def test_refund_create_adds_pending_refund_and_flushes(self) -> None:
        from app.models.enums import RefundStatus
        from app.repositories.refund_repository import create

        db = _FakeDb()
        merchant_db_id = uuid4()
        payment_transaction_id = uuid4()

        refund = create(
            db,
            refund_transaction_id="rfnd_123",
            merchant_db_id=merchant_db_id,
            payment_transaction_id=payment_transaction_id,
            refund_id="REF-1001",
            refund_amount=Decimal("100000.00"),
            reason="Customer requested refund",
            idempotency_key="idem-refund-1",
        )

        self.assertIs(db.added[0], refund)
        self.assertTrue(db.flushed)
        self.assertEqual(refund.status, RefundStatus.REFUND_PENDING)
        self.assertEqual(refund.refund_transaction_id, "rfnd_123")
        self.assertEqual(refund.idempotency_key, "idem-refund-1")


class RefundServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.models.enums import CredentialStatus, MerchantStatus
        from app.models.merchant import Merchant
        from app.models.merchant_credential import MerchantCredential
        from app.schemas.auth import AuthenticatedMerchant
        from app.schemas.refund import CreateRefundRequest

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
        self.payment = _payment(
            merchant_db_id=self.merchant.id,
            status="SUCCESS",
            paid_at=self.now - timedelta(hours=1),
        )
        self.request = CreateRefundRequest(
            original_transaction_id=self.payment.transaction_id,
            refund_id="REF-1001",
            refund_amount="100000.00",
            reason="Customer requested refund",
        )

    def test_successful_payment_can_create_refund_pending(self) -> None:
        from app.models.enums import RefundStatus
        from app.services.refund_service import create_refund

        db = _FakeDb()
        store = _RefundStore(payments=[self.payment])

        with store.patched_repositories():
            response = create_refund(
                db=db,
                authenticated_merchant=self.authenticated,
                request=self.request,
                idempotency_key="idem-refund-1",
                now=self.now,
            )

        self.assertTrue(db.committed)
        self.assertEqual(len(store.refunds), 1)
        refund = store.refunds[0]
        self.assertEqual(refund.status, RefundStatus.REFUND_PENDING)
        self.assertEqual(refund.idempotency_key, "idem-refund-1")
        self.assertEqual(response.original_transaction_id, self.payment.transaction_id)
        self.assertEqual(response.refund_status, RefundStatus.REFUND_PENDING)

    def test_order_id_request_resolves_successful_payment(self) -> None:
        from app.schemas.refund import CreateRefundRequest
        from app.services.refund_service import create_refund

        request = CreateRefundRequest(
            order_id=self.payment.order_id,
            refund_id="REF-1001",
            refund_amount="100000.00",
            reason="Customer requested refund",
        )
        store = _RefundStore(payments=[_payment(merchant_db_id=self.merchant.id, status="PENDING"), self.payment])

        with store.patched_repositories():
            response = create_refund(_FakeDb(), self.authenticated, request, None, now=self.now)

        self.assertEqual(response.original_transaction_id, self.payment.transaction_id)
        self.assertEqual(len(store.refunds), 1)

    def test_partial_refund_rejects(self) -> None:
        from app.core.errors import AppError
        from app.schemas.refund import CreateRefundRequest
        from app.services.refund_service import create_refund

        request = CreateRefundRequest(
            original_transaction_id=self.payment.transaction_id,
            refund_id="REF-1001",
            refund_amount="90000.00",
            reason="Customer requested partial refund",
        )
        store = _RefundStore(payments=[self.payment])

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                create_refund(_FakeDb(), self.authenticated, request, None, now=self.now)

        self.assertEqual(error.exception.error_code, "REFUND_AMOUNT_NOT_FULL")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(store.refunds), 0)

    def test_refund_after_7_day_window_rejects(self) -> None:
        from app.core.errors import AppError
        from app.services.refund_service import create_refund

        self.payment.paid_at = self.now - timedelta(days=7, seconds=1)
        store = _RefundStore(payments=[self.payment])

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                create_refund(_FakeDb(), self.authenticated, self.request, None, now=self.now)

        self.assertEqual(error.exception.error_code, "REFUND_WINDOW_EXPIRED")
        self.assertEqual(len(store.refunds), 0)

    def test_duplicate_refund_id_with_same_semantic_request_returns_existing_refund(self) -> None:
        from app.services.refund_service import create_refund

        store = _RefundStore(payments=[self.payment])

        with store.patched_repositories():
            first = create_refund(_FakeDb(), self.authenticated, self.request, "idem-1", now=self.now)
            second = create_refund(_FakeDb(), self.authenticated, self.request, "idem-2", now=self.now)

        self.assertEqual(first.refund_transaction_id, second.refund_transaction_id)
        self.assertEqual(len(store.refunds), 1)

    def test_duplicate_refund_id_with_conflicting_request_rejects(self) -> None:
        from app.core.errors import AppError
        from app.schemas.refund import CreateRefundRequest
        from app.services.refund_service import create_refund

        changed_request = CreateRefundRequest(
            original_transaction_id=self.payment.transaction_id,
            refund_id="REF-1001",
            refund_amount="100000.00",
            reason="Different reason",
        )
        store = _RefundStore(payments=[self.payment])

        with store.patched_repositories():
            create_refund(_FakeDb(), self.authenticated, self.request, "idem-1", now=self.now)
            with self.assertRaises(AppError) as error:
                create_refund(_FakeDb(), self.authenticated, changed_request, "idem-2", now=self.now)

        self.assertEqual(error.exception.error_code, "REFUND_NOT_ALLOWED")
        self.assertEqual(error.exception.status_code, 409)
        self.assertEqual(len(store.refunds), 1)

    def test_non_success_payment_rejects_refund(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import PaymentStatus
        from app.services.refund_service import create_refund

        for status in (PaymentStatus.PENDING, PaymentStatus.FAILED, PaymentStatus.EXPIRED):
            with self.subTest(status=status.value):
                payment = _payment(merchant_db_id=self.merchant.id, status=status)
                request = self.request.model_copy(update={"original_transaction_id": payment.transaction_id})
                store = _RefundStore(payments=[payment])

                with store.patched_repositories():
                    with self.assertRaises(AppError) as error:
                        create_refund(_FakeDb(), self.authenticated, request, None, now=self.now)

                self.assertEqual(error.exception.error_code, "PAYMENT_NOT_REFUNDABLE")
                self.assertEqual(len(store.refunds), 0)

    def test_success_payment_without_paid_at_rejects_refund(self) -> None:
        from app.core.errors import AppError
        from app.services.refund_service import create_refund

        self.payment.paid_at = None
        store = _RefundStore(payments=[self.payment])

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                create_refund(_FakeDb(), self.authenticated, self.request, None, now=self.now)

        self.assertEqual(error.exception.error_code, "PAYMENT_NOT_REFUNDABLE")

    def test_existing_pending_or_refunded_refund_blocks_new_refund_id(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import RefundStatus
        from app.schemas.refund import CreateRefundRequest
        from app.services.refund_service import create_refund

        for status in (RefundStatus.REFUND_PENDING, RefundStatus.REFUNDED):
            with self.subTest(status=status.value):
                existing_refund = _refund(payment=self.payment, status=status, refund_id="REF-OLD")
                store = _RefundStore(payments=[self.payment], refunds=[existing_refund])
                request = CreateRefundRequest(
                    original_transaction_id=self.payment.transaction_id,
                    refund_id="REF-NEW",
                    refund_amount="100000.00",
                    reason="Customer requested refund",
                )

                with store.patched_repositories():
                    with self.assertRaises(AppError) as error:
                        create_refund(_FakeDb(), self.authenticated, request, None, now=self.now)

                self.assertEqual(error.exception.error_code, "REFUND_NOT_ALLOWED")
                self.assertEqual(len(store.refunds), 1)

    def test_prior_failed_refund_does_not_block_new_refund_id(self) -> None:
        from app.models.enums import RefundStatus
        from app.schemas.refund import CreateRefundRequest
        from app.services.refund_service import create_refund

        existing_refund = _refund(payment=self.payment, status=RefundStatus.REFUND_FAILED, refund_id="REF-OLD")
        request = CreateRefundRequest(
            original_transaction_id=self.payment.transaction_id,
            refund_id="REF-NEW",
            refund_amount="100000.00",
            reason="Customer requested refund",
        )
        store = _RefundStore(payments=[self.payment], refunds=[existing_refund])

        with store.patched_repositories():
            response = create_refund(_FakeDb(), self.authenticated, request, None, now=self.now)

        self.assertEqual(response.refund_id, "REF-NEW")
        self.assertEqual(len(store.refunds), 2)

    def test_query_by_refund_transaction_id_and_refund_id_returns_owned_refund(self) -> None:
        from app.services.refund_service import get_refund_by_refund_id, get_refund_by_transaction_id

        refund = _refund(payment=self.payment)
        store = _RefundStore(payments=[self.payment], refunds=[refund])

        with store.patched_repositories():
            by_transaction = get_refund_by_transaction_id(
                _FakeDb(),
                self.authenticated,
                refund.refund_transaction_id,
            )
            by_refund_id = get_refund_by_refund_id(_FakeDb(), self.authenticated, refund.refund_id)

        self.assertEqual(by_transaction.refund_transaction_id, refund.refund_transaction_id)
        self.assertEqual(by_refund_id.refund_id, refund.refund_id)

    def test_query_foreign_refund_returns_not_found(self) -> None:
        from app.core.errors import AppError
        from app.services.refund_service import get_refund_by_transaction_id

        foreign_payment = _payment(status="SUCCESS", paid_at=self.now, merchant_db_id=uuid4())
        foreign_refund = _refund(payment=foreign_payment)
        store = _RefundStore(payments=[foreign_payment], refunds=[foreign_refund])

        with store.patched_repositories():
            with self.assertRaises(AppError) as error:
                get_refund_by_transaction_id(_FakeDb(), self.authenticated, foreign_refund.refund_transaction_id)

        self.assertEqual(error.exception.error_code, "REFUND_NOT_FOUND")
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


class _RefundStore:
    def __init__(self, payments=None, refunds=None) -> None:
        self.payments = payments or []
        self.refunds = refunds or []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.refund_service.payment_repository.get_by_transaction_id",
                side_effect=self.get_payment_by_transaction_id,
            ),
            patch(
                "app.services.refund_service.payment_repository.get_success_by_merchant_order",
                side_effect=self.get_success_by_merchant_order,
            ),
            patch(
                "app.services.refund_service.payment_repository.get_by_id",
                side_effect=self.get_payment_by_id,
            ),
            patch(
                "app.services.refund_service.refund_repository.get_by_merchant_refund_id",
                side_effect=self.get_by_merchant_refund_id,
            ),
            patch(
                "app.services.refund_service.refund_repository.get_by_refund_transaction_id",
                side_effect=self.get_by_refund_transaction_id,
            ),
            patch(
                "app.services.refund_service.refund_repository.get_by_payment_and_statuses",
                side_effect=self.get_by_payment_and_statuses,
            ),
            patch(
                "app.services.refund_service.refund_repository.create",
                side_effect=self.create_refund,
            ),
        )

    def get_payment_by_transaction_id(self, db, transaction_id):
        for payment in self.payments:
            if payment.transaction_id == transaction_id:
                return payment
        return None

    def get_payment_by_id(self, db, payment_id):
        for payment in self.payments:
            if payment.id == payment_id:
                return payment
        return None

    def get_success_by_merchant_order(self, db, merchant_db_id, order_id):
        from app.models.enums import PaymentStatus

        for payment in reversed(self.payments):
            if (
                payment.merchant_db_id == merchant_db_id
                and payment.order_id == order_id
                and payment.status == PaymentStatus.SUCCESS
            ):
                return payment
        return None

    def get_by_merchant_refund_id(self, db, merchant_db_id, refund_id):
        for refund in self.refunds:
            if refund.merchant_db_id == merchant_db_id and refund.refund_id == refund_id:
                return refund
        return None

    def get_by_refund_transaction_id(self, db, refund_transaction_id):
        for refund in self.refunds:
            if refund.refund_transaction_id == refund_transaction_id:
                return refund
        return None

    def get_by_payment_and_statuses(self, db, payment_transaction_id, statuses):
        statuses = set(statuses)
        for refund in self.refunds:
            if refund.payment_transaction_id == payment_transaction_id and refund.status in statuses:
                return refund
        return None

    def create_refund(self, db, **kwargs):
        from app.models.enums import RefundStatus
        from app.models.refund_transaction import RefundTransaction

        refund = RefundTransaction(
            id=uuid4(),
            status=RefundStatus.REFUND_PENDING,
            **kwargs,
        )
        self.refunds.append(refund)
        return refund


class _PatchGroup:
    def __init__(self, *patches) -> None:
        self.patches = patches

    def __enter__(self):
        for patcher in self.patches:
            patcher.__enter__()

    def __exit__(self, exc_type, exc, traceback):
        for patcher in reversed(self.patches):
            patcher.__exit__(exc_type, exc, traceback)


def _payment(
    status,
    paid_at=None,
    merchant_db_id=None,
    transaction_id="pay_123",
    order_id="ORDER-1001",
):
    from app.models.enums import PaymentStatus
    from app.models.payment_transaction import PaymentTransaction

    if isinstance(status, str):
        status = PaymentStatus(status)
    return PaymentTransaction(
        id=uuid4(),
        transaction_id=transaction_id,
        merchant_db_id=merchant_db_id or uuid4(),
        order_reference_id=uuid4(),
        order_id=order_id,
        amount=Decimal("100000.00"),
        currency="VND",
        description="Demo QR payment",
        status=status,
        qr_content="MINI_GATEWAY|...",
        expire_at=datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc),
        paid_at=paid_at,
    )


def _refund(payment, status="REFUND_PENDING", refund_id="REF-1001"):
    from app.models.enums import RefundStatus
    from app.models.refund_transaction import RefundTransaction

    if isinstance(status, str):
        status = RefundStatus(status)
    return RefundTransaction(
        id=uuid4(),
        refund_transaction_id="rfnd_123",
        merchant_db_id=payment.merchant_db_id,
        payment_transaction_id=payment.id,
        refund_id=refund_id,
        refund_amount=Decimal("100000.00"),
        reason="Customer requested refund",
        status=status,
    )


if __name__ == "__main__":
    unittest.main()
