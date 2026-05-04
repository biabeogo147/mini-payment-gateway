import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class WebhookHookTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.schemas.provider_callback import PaymentCallbackRequest, RefundCallbackRequest

        self.now = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)
        self.payment_success_request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="SUCCESS",
            amount="100000.00",
            paid_at=self.now,
            raw_payload={"trace_id": "trace-1001"},
        )
        self.payment_failed_request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="FAILED",
            amount="100000.00",
            failed_reason_code="BANK_REJECTED",
            failed_reason_message="Bank rejected payment.",
            raw_payload={"trace_id": "trace-1001"},
        )
        self.refund_success_request = RefundCallbackRequest(
            external_reference="bank-refund-1001",
            refund_transaction_id="rfnd_123",
            status="SUCCESS",
            amount="100000.00",
            processed_at=self.now,
            raw_payload={"trace_id": "refund-trace-1001"},
        )
        self.refund_failed_request = RefundCallbackRequest(
            external_reference="bank-refund-1001",
            refund_transaction_id="rfnd_123",
            status="FAILED",
            amount="100000.00",
            failed_reason_code="BANK_REJECTED",
            failed_reason_message="Bank rejected refund.",
            raw_payload={"trace_id": "refund-trace-1001"},
        )

    def test_payment_success_and_failed_callbacks_create_webhook_events(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.provider_callback_service import process_payment_callback

        for request, expected_status in (
            (self.payment_success_request, PaymentStatus.SUCCESS),
            (self.payment_failed_request, PaymentStatus.FAILED),
        ):
            with self.subTest(status=request.status.value):
                payment = _payment(status=PaymentStatus.PENDING)
                store = _CallbackStore(payments=[payment])

                with store.patched_repositories(), patch(
                    "app.services.provider_callback_service.webhook_event_factory.create_payment_event_if_needed"
                ) as create_event:
                    process_payment_callback(_FakeDb(), request, now=self.now)

                self.assertEqual(payment.status, expected_status)
                create_event.assert_called_once()
                self.assertIs(create_event.call_args.args[1], payment)

    def test_duplicate_and_pending_review_payment_callbacks_do_not_create_webhook_event(self) -> None:
        from app.models.enums import PaymentStatus
        from app.schemas.provider_callback import PaymentCallbackRequest
        from app.services.provider_callback_service import process_payment_callback

        duplicate_payment = _payment(status=PaymentStatus.SUCCESS)
        mismatch_payment = _payment(status=PaymentStatus.PENDING)
        mismatch_request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="SUCCESS",
            amount="200000.00",
            paid_at=self.now,
            raw_payload={"trace_id": "trace-1001"},
        )

        cases = (
            (_CallbackStore(payments=[duplicate_payment]), self.payment_success_request),
            (_CallbackStore(payments=[mismatch_payment]), mismatch_request),
        )

        for store, request in cases:
            with self.subTest(status=request.status.value, amount=str(request.amount)):
                with store.patched_repositories(), patch(
                    "app.services.provider_callback_service.webhook_event_factory.create_payment_event_if_needed"
                ) as create_event:
                    process_payment_callback(_FakeDb(), request, now=self.now)

                create_event.assert_not_called()

    def test_expiration_service_creates_payment_expired_events(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.expiration_service import expire_overdue_payments

        payment = _payment(status=PaymentStatus.PENDING)
        store = _ExpirationStore(payments=[payment])

        with store.patched_repositories(), patch(
            "app.services.expiration_service.webhook_event_factory.create_payment_event_if_needed"
        ) as create_event:
            expired_count = expire_overdue_payments(_FakeDb(), now=self.now)

        self.assertEqual(expired_count, 1)
        self.assertEqual(payment.status, PaymentStatus.EXPIRED)
        create_event.assert_called_once()
        self.assertIs(create_event.call_args.args[1], payment)

    def test_refund_success_and_failed_callbacks_create_webhook_events(self) -> None:
        from app.models.enums import RefundStatus
        from app.services.provider_callback_service import process_refund_callback

        for request, expected_status in (
            (self.refund_success_request, RefundStatus.REFUNDED),
            (self.refund_failed_request, RefundStatus.REFUND_FAILED),
        ):
            with self.subTest(status=request.status.value):
                refund = _refund(status=RefundStatus.REFUND_PENDING)
                store = _RefundCallbackStore(refunds=[refund])

                with store.patched_repositories(), patch(
                    "app.services.provider_callback_service.webhook_event_factory.create_refund_event_if_needed"
                ) as create_event:
                    process_refund_callback(_FakeDb(), request, now=self.now)

                self.assertEqual(refund.status, expected_status)
                create_event.assert_called_once()
                self.assertIs(create_event.call_args.args[1], refund)


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


class _CallbackStore:
    def __init__(self, payments) -> None:
        self.payments = payments
        self.callback_logs = []
        self.reconciliation_records = []
        self.saved_payments = []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.provider_callback_service.payment_repository.get_by_transaction_id",
                side_effect=self.get_payment_by_transaction_id,
            ),
            patch(
                "app.services.provider_callback_service.payment_repository.save",
                side_effect=self.save_payment,
            ),
            patch(
                "app.services.provider_callback_service.bank_callback_repository.create_payment_callback_log",
                side_effect=self.create_callback_log,
            ),
            patch(
                "app.services.provider_callback_service.reconciliation_repository.create_payment_reconciliation_record",
                side_effect=self.create_reconciliation_record,
            ),
        )

    def get_payment_by_transaction_id(self, db, transaction_id):
        for payment in self.payments:
            if payment.transaction_id == transaction_id:
                return payment
        return None

    def save_payment(self, db, payment):
        self.saved_payments.append(payment)
        return payment

    def create_callback_log(self, db, **kwargs):
        self.callback_logs.append(kwargs)
        return kwargs

    def create_reconciliation_record(self, db, **kwargs):
        from app.models.enums import EntityType
        from app.models.reconciliation_record import ReconciliationRecord

        payment = kwargs["payment"]
        record = ReconciliationRecord(
            id=uuid4(),
            entity_type=EntityType.PAYMENT,
            entity_id=payment.id,
            internal_status=payment.status.value,
            external_status=kwargs["external_status"],
            internal_amount=payment.amount,
            external_amount=kwargs["external_amount"],
            match_result=kwargs["match_result"],
            mismatch_reason_code=kwargs.get("mismatch_reason_code"),
            mismatch_reason_message=kwargs.get("mismatch_reason_message"),
        )
        self.reconciliation_records.append(record)
        return record


class _RefundCallbackStore:
    def __init__(self, refunds) -> None:
        self.refunds = refunds
        self.callback_logs = []
        self.saved_refunds = []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.provider_callback_service.refund_repository.get_by_refund_transaction_id",
                side_effect=self.get_refund_by_transaction_id,
            ),
            patch(
                "app.services.provider_callback_service.refund_repository.save",
                side_effect=self.save_refund,
            ),
            patch(
                "app.services.provider_callback_service.bank_callback_repository.create_refund_callback_log",
                side_effect=self.create_callback_log,
            ),
        )

    def get_refund_by_transaction_id(self, db, refund_transaction_id):
        for refund in self.refunds:
            if refund.refund_transaction_id == refund_transaction_id:
                return refund
        return None

    def save_refund(self, db, refund):
        self.saved_refunds.append(refund)
        return refund

    def create_callback_log(self, db, **kwargs):
        self.callback_logs.append(kwargs)
        return kwargs


class _ExpirationStore:
    def __init__(self, payments) -> None:
        self.payments = payments
        self.saved_payments = []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.expiration_service.payment_repository.find_overdue_pending",
                return_value=self.payments,
            ),
            patch(
                "app.services.expiration_service.payment_repository.save",
                side_effect=self.save_payment,
            ),
        )

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


def _payment(status):
    from app.models.enums import PaymentStatus
    from app.models.payment_transaction import PaymentTransaction

    if isinstance(status, str):
        status = PaymentStatus(status)
    return PaymentTransaction(
        id=uuid4(),
        transaction_id="pay_123",
        merchant_db_id=uuid4(),
        order_reference_id=uuid4(),
        order_id="ORDER-1001",
        amount=Decimal("100000.00"),
        currency="VND",
        description="Demo QR payment",
        status=status,
        qr_content="MINI_GATEWAY|...",
        expire_at=datetime(2026, 4, 29, 10, 15, tzinfo=timezone.utc),
    )


def _refund(status):
    from app.models.enums import RefundStatus
    from app.models.refund_transaction import RefundTransaction

    if isinstance(status, str):
        status = RefundStatus(status)
    return RefundTransaction(
        id=uuid4(),
        refund_transaction_id="rfnd_123",
        merchant_db_id=uuid4(),
        payment_transaction_id=uuid4(),
        refund_id="REF-1001",
        refund_amount=Decimal("100000.00"),
        reason="Customer requested refund",
        status=status,
    )


if __name__ == "__main__":
    unittest.main()
