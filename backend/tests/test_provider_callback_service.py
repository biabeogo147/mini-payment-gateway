import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class ProviderCallbackSchemaTest(unittest.TestCase):
    def test_success_callback_requires_paid_at(self) -> None:
        from pydantic import ValidationError

        from app.schemas.provider_callback import PaymentCallbackRequest

        with self.assertRaises(ValidationError):
            PaymentCallbackRequest(
                external_reference="bank-ref-1001",
                transaction_reference="pay_123",
                status="SUCCESS",
                amount="100000.00",
                raw_payload={"trace_id": "trace-1001"},
            )

    def test_failed_callback_accepts_failed_reason_fields(self) -> None:
        from app.models.enums import CallbackSourceType
        from app.schemas.provider_callback import PaymentCallbackRequest, PaymentCallbackStatus

        request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="FAILED",
            amount="100000.00",
            failed_reason_code="BANK_REJECTED",
            failed_reason_message="Bank rejected payment.",
            raw_payload={"trace_id": "trace-1001"},
        )

        self.assertEqual(request.status, PaymentCallbackStatus.FAILED)
        self.assertEqual(request.source_type, CallbackSourceType.SIMULATOR)
        self.assertEqual(request.failed_reason_code, "BANK_REJECTED")

    def test_unsupported_status_rejects(self) -> None:
        from pydantic import ValidationError

        from app.schemas.provider_callback import PaymentCallbackRequest

        with self.assertRaises(ValidationError):
            PaymentCallbackRequest(
                external_reference="bank-ref-1001",
                transaction_reference="pay_123",
                status="PENDING",
                amount="100000.00",
                raw_payload={"trace_id": "trace-1001"},
            )

    def test_refund_success_callback_requires_processed_at(self) -> None:
        from pydantic import ValidationError

        from app.schemas.provider_callback import RefundCallbackRequest

        with self.assertRaises(ValidationError):
            RefundCallbackRequest(
                external_reference="bank-refund-1001",
                refund_transaction_id="rfnd_123",
                status="SUCCESS",
                amount="100000.00",
                raw_payload={"trace_id": "refund-trace-1001"},
            )

    def test_refund_failed_callback_accepts_failed_reason_fields(self) -> None:
        from app.models.enums import CallbackSourceType
        from app.schemas.provider_callback import RefundCallbackRequest, RefundCallbackStatus

        request = RefundCallbackRequest(
            external_reference="bank-refund-1001",
            refund_transaction_id="rfnd_123",
            status="FAILED",
            amount="100000.00",
            failed_reason_code="BANK_REJECTED",
            failed_reason_message="Bank rejected refund.",
            raw_payload={"trace_id": "refund-trace-1001"},
        )

        self.assertEqual(request.status, RefundCallbackStatus.FAILED)
        self.assertEqual(request.source_type, CallbackSourceType.SIMULATOR)
        self.assertEqual(request.failed_reason_code, "BANK_REJECTED")

    def test_refund_unsupported_status_rejects(self) -> None:
        from pydantic import ValidationError

        from app.schemas.provider_callback import RefundCallbackRequest

        with self.assertRaises(ValidationError):
            RefundCallbackRequest(
                external_reference="bank-refund-1001",
                refund_transaction_id="rfnd_123",
                status="REFUNDED",
                amount="100000.00",
                processed_at=datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc),
                raw_payload={"trace_id": "refund-trace-1001"},
            )


class CallbackRepositoryTest(unittest.TestCase):
    def test_create_payment_callback_log_adds_and_flushes(self) -> None:
        from app.models.enums import CallbackProcessingResult, CallbackSourceType
        from app.repositories.bank_callback_repository import create_payment_callback_log

        db = _FakeDb()
        received_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)

        log = create_payment_callback_log(
            db=db,
            source_type=CallbackSourceType.SIMULATOR,
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            raw_payload={"trace_id": "trace-1001"},
            normalized_status="SUCCESS",
            received_at=received_at,
            processed_at=received_at,
            processing_result=CallbackProcessingResult.PROCESSED,
        )

        self.assertIs(db.added[0], log)
        self.assertTrue(db.flushed)
        self.assertEqual(log.raw_payload_json, {"trace_id": "trace-1001"})
        self.assertEqual(log.transaction_reference, "pay_123")
        self.assertEqual(log.processing_result, CallbackProcessingResult.PROCESSED)

    def test_create_payment_reconciliation_record_adds_and_flushes(self) -> None:
        from app.models.enums import ReconciliationStatus
        from app.repositories.reconciliation_repository import create_payment_reconciliation_record

        db = _FakeDb()
        payment = _payment(status="PENDING")

        record = create_payment_reconciliation_record(
            db=db,
            payment=payment,
            external_status="SUCCESS",
            external_amount=Decimal("200000.00"),
            match_result=ReconciliationStatus.MISMATCHED,
            mismatch_reason_code="AMOUNT_MISMATCH",
            mismatch_reason_message="Callback amount does not match payment amount.",
        )

        self.assertIs(db.added[0], record)
        self.assertTrue(db.flushed)
        self.assertEqual(record.entity_id, payment.id)
        self.assertEqual(record.internal_status, "PENDING")
        self.assertEqual(record.external_status, "SUCCESS")
        self.assertEqual(record.internal_amount, Decimal("100000.00"))
        self.assertEqual(record.external_amount, Decimal("200000.00"))
        self.assertEqual(record.match_result, ReconciliationStatus.MISMATCHED)

    def test_create_refund_callback_log_adds_refund_result_type(self) -> None:
        from app.models.enums import CallbackProcessingResult, CallbackSourceType, CallbackType
        from app.repositories.bank_callback_repository import create_refund_callback_log

        db = _FakeDb()
        received_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)

        log = create_refund_callback_log(
            db=db,
            source_type=CallbackSourceType.SIMULATOR,
            external_reference="bank-refund-1001",
            transaction_reference="rfnd_123",
            raw_payload={"trace_id": "refund-trace-1001"},
            normalized_status="SUCCESS",
            received_at=received_at,
            processed_at=received_at,
            processing_result=CallbackProcessingResult.PROCESSED,
        )

        self.assertIs(db.added[0], log)
        self.assertTrue(db.flushed)
        self.assertEqual(log.callback_type, CallbackType.REFUND_RESULT)
        self.assertEqual(log.transaction_reference, "rfnd_123")
        self.assertEqual(log.processing_result, CallbackProcessingResult.PROCESSED)

    def test_create_refund_reconciliation_record_adds_and_flushes(self) -> None:
        from app.models.enums import ReconciliationStatus
        from app.repositories.reconciliation_repository import create_refund_reconciliation_record

        db = _FakeDb()
        refund = _refund(status="REFUND_PENDING")

        record = create_refund_reconciliation_record(
            db=db,
            refund=refund,
            external_status="SUCCESS",
            external_amount=Decimal("200000.00"),
            match_result=ReconciliationStatus.MISMATCHED,
            mismatch_reason_code="AMOUNT_MISMATCH",
            mismatch_reason_message="Callback amount does not match refund amount.",
        )

        self.assertIs(db.added[0], record)
        self.assertTrue(db.flushed)
        self.assertEqual(record.entity_id, refund.id)
        self.assertEqual(record.internal_status, "REFUND_PENDING")
        self.assertEqual(record.external_status, "SUCCESS")
        self.assertEqual(record.internal_amount, Decimal("100000.00"))
        self.assertEqual(record.external_amount, Decimal("200000.00"))
        self.assertEqual(record.match_result, ReconciliationStatus.MISMATCHED)


class ProviderCallbackServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.schemas.provider_callback import PaymentCallbackRequest

        self.now = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)
        self.success_request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="SUCCESS",
            amount="100000.00",
            paid_at=self.now,
            raw_payload={"trace_id": "trace-1001"},
        )
        self.failed_request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="FAILED",
            amount="100000.00",
            failed_reason_code="BANK_REJECTED",
            failed_reason_message="Bank rejected payment.",
            raw_payload={"trace_id": "trace-1001"},
        )

    def test_success_callback_marks_pending_payment_success_and_logs_evidence(self) -> None:
        from app.models.enums import CallbackProcessingResult, PaymentStatus
        from app.services.provider_callback_service import process_payment_callback

        db = _FakeDb()
        store = _CallbackStore(payments=[_payment(status=PaymentStatus.PENDING)])

        with store.patched_repositories():
            response = process_payment_callback(db, self.success_request, now=self.now)

        payment = store.payments[0]
        self.assertTrue(db.committed)
        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(payment.paid_at, self.now)
        self.assertEqual(payment.external_reference, "bank-ref-1001")
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PROCESSED)
        self.assertEqual(response.transaction_id, "pay_123")
        self.assertEqual(response.status, PaymentStatus.SUCCESS)
        self.assertEqual(response.processing_result, CallbackProcessingResult.PROCESSED)

    def test_failed_callback_marks_pending_payment_failed_and_logs_evidence(self) -> None:
        from app.models.enums import CallbackProcessingResult, PaymentStatus
        from app.services.provider_callback_service import process_payment_callback

        db = _FakeDb()
        store = _CallbackStore(payments=[_payment(status=PaymentStatus.PENDING)])

        with store.patched_repositories():
            response = process_payment_callback(db, self.failed_request, now=self.now)

        payment = store.payments[0]
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(payment.failed_reason_code, "BANK_REJECTED")
        self.assertEqual(payment.failed_reason_message, "Bank rejected payment.")
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PROCESSED)
        self.assertEqual(response.status, PaymentStatus.FAILED)

    def test_unknown_transaction_logs_pending_review_without_server_error(self) -> None:
        from app.models.enums import CallbackProcessingResult
        from app.services.provider_callback_service import process_payment_callback

        db = _FakeDb()
        store = _CallbackStore(payments=[])

        with store.patched_repositories():
            response = process_payment_callback(db, self.success_request, now=self.now)

        self.assertTrue(db.committed)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertIsNone(response.transaction_id)
        self.assertIsNone(response.status)
        self.assertEqual(response.processing_result, CallbackProcessingResult.PENDING_REVIEW)

    def test_duplicate_same_state_callback_is_ignored_without_mutating_payment(self) -> None:
        from app.models.enums import CallbackProcessingResult, PaymentStatus
        from app.services.provider_callback_service import process_payment_callback

        paid_at = datetime(2026, 4, 29, 10, 4, tzinfo=timezone.utc)
        payment = _payment(status=PaymentStatus.SUCCESS)
        payment.paid_at = paid_at
        store = _CallbackStore(payments=[payment])

        with store.patched_repositories():
            response = process_payment_callback(_FakeDb(), self.success_request, now=self.now)

        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(payment.paid_at, paid_at)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.IGNORED)
        self.assertEqual(response.status, PaymentStatus.SUCCESS)
        self.assertEqual(response.processing_result, CallbackProcessingResult.IGNORED)

    def test_amount_mismatch_creates_reconciliation_and_does_not_mark_success(self) -> None:
        from app.models.enums import CallbackProcessingResult, PaymentStatus, ReconciliationStatus
        from app.schemas.provider_callback import PaymentCallbackRequest
        from app.services.provider_callback_service import process_payment_callback

        mismatch_request = PaymentCallbackRequest(
            external_reference="bank-ref-1001",
            transaction_reference="pay_123",
            status="SUCCESS",
            amount="200000.00",
            paid_at=self.now,
            raw_payload={"trace_id": "trace-1001"},
        )
        payment = _payment(status=PaymentStatus.PENDING)
        store = _CallbackStore(payments=[payment])

        with store.patched_repositories():
            response = process_payment_callback(_FakeDb(), mismatch_request, now=self.now)

        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertEqual(store.reconciliation_records[0].match_result, ReconciliationStatus.MISMATCHED)
        self.assertEqual(store.reconciliation_records[0].mismatch_reason_code, "AMOUNT_MISMATCH")
        self.assertEqual(response.processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertIsNotNone(response.reconciliation_record_id)

    def test_late_success_after_expiration_creates_reconciliation_and_does_not_revive(self) -> None:
        from app.models.enums import CallbackProcessingResult, PaymentStatus, ReconciliationStatus
        from app.services.provider_callback_service import process_payment_callback

        payment = _payment(status=PaymentStatus.EXPIRED)
        store = _CallbackStore(payments=[payment])

        with store.patched_repositories():
            response = process_payment_callback(_FakeDb(), self.success_request, now=self.now)

        self.assertEqual(payment.status, PaymentStatus.EXPIRED)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertEqual(store.reconciliation_records[0].match_result, ReconciliationStatus.PENDING_REVIEW)
        self.assertEqual(store.reconciliation_records[0].mismatch_reason_code, "LATE_SUCCESS_AFTER_EXPIRATION")
        self.assertEqual(response.status, PaymentStatus.EXPIRED)
        self.assertEqual(response.processing_result, CallbackProcessingResult.PENDING_REVIEW)


class RefundProviderCallbackServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.schemas.provider_callback import RefundCallbackRequest

        self.now = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)
        self.success_request = RefundCallbackRequest(
            external_reference="bank-refund-1001",
            refund_transaction_id="rfnd_123",
            status="SUCCESS",
            amount="100000.00",
            processed_at=self.now,
            raw_payload={"trace_id": "refund-trace-1001"},
        )
        self.failed_request = RefundCallbackRequest(
            external_reference="bank-refund-1001",
            refund_transaction_id="rfnd_123",
            status="FAILED",
            amount="100000.00",
            failed_reason_code="BANK_REJECTED",
            failed_reason_message="Bank rejected refund.",
            raw_payload={"trace_id": "refund-trace-1001"},
        )

    def test_success_callback_marks_pending_refund_refunded_and_logs_evidence(self) -> None:
        from app.models.enums import CallbackProcessingResult, RefundStatus
        from app.services.provider_callback_service import process_refund_callback

        db = _FakeDb()
        store = _RefundCallbackStore(refunds=[_refund(status=RefundStatus.REFUND_PENDING)])

        with store.patched_repositories():
            response = process_refund_callback(db, self.success_request, now=self.now)

        refund = store.refunds[0]
        self.assertTrue(db.committed)
        self.assertEqual(refund.status, RefundStatus.REFUNDED)
        self.assertEqual(refund.processed_at, self.now)
        self.assertEqual(refund.external_reference, "bank-refund-1001")
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PROCESSED)
        self.assertEqual(response.refund_transaction_id, "rfnd_123")
        self.assertEqual(response.refund_status, RefundStatus.REFUNDED)
        self.assertEqual(response.processing_result, CallbackProcessingResult.PROCESSED)

    def test_failed_callback_marks_pending_refund_failed_and_logs_evidence(self) -> None:
        from app.models.enums import CallbackProcessingResult, RefundStatus
        from app.services.provider_callback_service import process_refund_callback

        store = _RefundCallbackStore(refunds=[_refund(status=RefundStatus.REFUND_PENDING)])

        with store.patched_repositories():
            response = process_refund_callback(_FakeDb(), self.failed_request, now=self.now)

        refund = store.refunds[0]
        self.assertEqual(refund.status, RefundStatus.REFUND_FAILED)
        self.assertEqual(refund.failed_reason_code, "BANK_REJECTED")
        self.assertEqual(refund.failed_reason_message, "Bank rejected refund.")
        self.assertEqual(refund.processed_at, self.now)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PROCESSED)
        self.assertEqual(response.refund_status, RefundStatus.REFUND_FAILED)

    def test_unknown_refund_logs_pending_review_without_server_error(self) -> None:
        from app.models.enums import CallbackProcessingResult
        from app.services.provider_callback_service import process_refund_callback

        db = _FakeDb()
        store = _RefundCallbackStore(refunds=[])

        with store.patched_repositories():
            response = process_refund_callback(db, self.success_request, now=self.now)

        self.assertTrue(db.committed)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertIsNone(response.refund_transaction_id)
        self.assertIsNone(response.refund_status)
        self.assertEqual(response.processing_result, CallbackProcessingResult.PENDING_REVIEW)

    def test_duplicate_same_state_callback_is_ignored_without_mutating_refund(self) -> None:
        from app.models.enums import CallbackProcessingResult, RefundStatus
        from app.services.provider_callback_service import process_refund_callback

        processed_at = datetime(2026, 4, 29, 10, 4, tzinfo=timezone.utc)
        refund = _refund(status=RefundStatus.REFUNDED)
        refund.processed_at = processed_at
        store = _RefundCallbackStore(refunds=[refund])

        with store.patched_repositories():
            response = process_refund_callback(_FakeDb(), self.success_request, now=self.now)

        self.assertEqual(refund.status, RefundStatus.REFUNDED)
        self.assertEqual(refund.processed_at, processed_at)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.IGNORED)
        self.assertEqual(response.refund_status, RefundStatus.REFUNDED)
        self.assertEqual(response.processing_result, CallbackProcessingResult.IGNORED)

    def test_amount_mismatch_creates_reconciliation_and_does_not_mark_refunded(self) -> None:
        from app.models.enums import CallbackProcessingResult, ReconciliationStatus, RefundStatus
        from app.schemas.provider_callback import RefundCallbackRequest
        from app.services.provider_callback_service import process_refund_callback

        mismatch_request = RefundCallbackRequest(
            external_reference="bank-refund-1001",
            refund_transaction_id="rfnd_123",
            status="SUCCESS",
            amount="200000.00",
            processed_at=self.now,
            raw_payload={"trace_id": "refund-trace-1001"},
        )
        refund = _refund(status=RefundStatus.REFUND_PENDING)
        store = _RefundCallbackStore(refunds=[refund])

        with store.patched_repositories():
            response = process_refund_callback(_FakeDb(), mismatch_request, now=self.now)

        self.assertEqual(refund.status, RefundStatus.REFUND_PENDING)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertEqual(store.reconciliation_records[0].match_result, ReconciliationStatus.MISMATCHED)
        self.assertEqual(store.reconciliation_records[0].mismatch_reason_code, "AMOUNT_MISMATCH")
        self.assertEqual(response.processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertIsNotNone(response.reconciliation_record_id)

    def test_final_state_conflict_creates_reconciliation_and_does_not_mutate(self) -> None:
        from app.models.enums import CallbackProcessingResult, ReconciliationStatus, RefundStatus
        from app.services.provider_callback_service import process_refund_callback

        refund = _refund(status=RefundStatus.REFUNDED)
        store = _RefundCallbackStore(refunds=[refund])

        with store.patched_repositories():
            response = process_refund_callback(_FakeDb(), self.failed_request, now=self.now)

        self.assertEqual(refund.status, RefundStatus.REFUNDED)
        self.assertEqual(store.callback_logs[0].processing_result, CallbackProcessingResult.PENDING_REVIEW)
        self.assertEqual(store.reconciliation_records[0].match_result, ReconciliationStatus.PENDING_REVIEW)
        self.assertEqual(store.reconciliation_records[0].mismatch_reason_code, "STATUS_CONFLICT")
        self.assertEqual(response.refund_status, RefundStatus.REFUNDED)
        self.assertEqual(response.processing_result, CallbackProcessingResult.PENDING_REVIEW)


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
            patch(
                "app.services.provider_callback_service.webhook_event_factory.create_payment_event_if_needed",
                return_value=None,
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
        from app.models.enums import CallbackType
        from app.models.bank_callback_log import BankCallbackLog

        log = BankCallbackLog(
            id=uuid4(),
            source_type=kwargs["source_type"],
            external_reference=kwargs["external_reference"],
            transaction_reference=kwargs["transaction_reference"],
            callback_type=CallbackType.PAYMENT_RESULT,
            raw_payload_json=kwargs["raw_payload"],
            normalized_status=kwargs["normalized_status"],
            received_at=kwargs["received_at"],
            processed_at=kwargs["processed_at"],
            processing_result=kwargs["processing_result"],
            error_message=kwargs.get("error_message"),
        )
        self.callback_logs.append(log)
        return log

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
            internal_amount=Decimal(payment.amount),
            external_amount=kwargs["external_amount"],
            match_result=kwargs["match_result"],
            mismatch_reason_code=kwargs.get("mismatch_reason_code"),
            mismatch_reason_message=kwargs.get("mismatch_reason_message"),
        )
        self.reconciliation_records.append(record)
        return record


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


class _RefundCallbackStore:
    def __init__(self, refunds) -> None:
        self.refunds = refunds
        self.callback_logs = []
        self.reconciliation_records = []
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
            patch(
                "app.services.provider_callback_service.reconciliation_repository.create_refund_reconciliation_record",
                side_effect=self.create_reconciliation_record,
            ),
            patch(
                "app.services.provider_callback_service.webhook_event_factory.create_refund_event_if_needed",
                return_value=None,
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
        from app.models.enums import CallbackType
        from app.models.bank_callback_log import BankCallbackLog

        log = BankCallbackLog(
            id=uuid4(),
            source_type=kwargs["source_type"],
            external_reference=kwargs["external_reference"],
            transaction_reference=kwargs["transaction_reference"],
            callback_type=CallbackType.REFUND_RESULT,
            raw_payload_json=kwargs["raw_payload"],
            normalized_status=kwargs["normalized_status"],
            received_at=kwargs["received_at"],
            processed_at=kwargs["processed_at"],
            processing_result=kwargs["processing_result"],
            error_message=kwargs.get("error_message"),
        )
        self.callback_logs.append(log)
        return log

    def create_reconciliation_record(self, db, **kwargs):
        from app.models.enums import EntityType
        from app.models.reconciliation_record import ReconciliationRecord

        refund = kwargs["refund"]
        record = ReconciliationRecord(
            id=uuid4(),
            entity_type=EntityType.REFUND,
            entity_id=refund.id,
            internal_status=refund.status.value,
            external_status=kwargs["external_status"],
            internal_amount=Decimal(refund.refund_amount),
            external_amount=kwargs["external_amount"],
            match_result=kwargs["match_result"],
            mismatch_reason_code=kwargs.get("mismatch_reason_code"),
            mismatch_reason_message=kwargs.get("mismatch_reason_message"),
        )
        self.reconciliation_records.append(record)
        return record


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
