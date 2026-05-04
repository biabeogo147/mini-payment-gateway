import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4


class ReconciliationRepositoryTest(unittest.TestCase):
    def test_get_find_and_save_records(self) -> None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.models.enums import EntityType, ReconciliationStatus
        from app.models.internal_user import InternalUser
        from app.models.reconciliation_record import ReconciliationRecord
        from app.repositories import reconciliation_repository

        engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        InternalUser.__table__.create(engine)
        ReconciliationRecord.__table__.create(engine)
        Session = sessionmaker(bind=engine, future=True)
        payment_id = uuid4()
        refund_id = uuid4()

        with Session() as db:
            payment_record = ReconciliationRecord(
                id=uuid4(),
                entity_type=EntityType.PAYMENT,
                entity_id=payment_id,
                internal_status="PENDING",
                external_status="SUCCESS",
                internal_amount=Decimal("100000.00"),
                external_amount=Decimal("100000.00"),
                match_result=ReconciliationStatus.PENDING_REVIEW,
            )
            refund_record = ReconciliationRecord(
                id=uuid4(),
                entity_type=EntityType.REFUND,
                entity_id=refund_id,
                internal_status="REFUNDED",
                external_status="SUCCESS",
                internal_amount=Decimal("50000.00"),
                external_amount=Decimal("50000.00"),
                match_result=ReconciliationStatus.MATCHED,
            )
            db.add_all([payment_record, refund_record])
            db.commit()

            fetched = reconciliation_repository.get_by_id(db, payment_record.id)
            matched = reconciliation_repository.find(db, match_result=ReconciliationStatus.MATCHED)
            payment_records = reconciliation_repository.find(db, entity_type=EntityType.PAYMENT, entity_id=payment_id)
            payment_record.review_note = "Reviewed."
            saved = reconciliation_repository.save(db, payment_record)

            self.assertEqual(fetched.id, payment_record.id)
            self.assertEqual([record.id for record in matched], [refund_record.id])
            self.assertEqual([record.id for record in payment_records], [payment_record.id])
            self.assertIs(saved, payment_record)


class ReconciliationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.models.enums import ActorType
        from app.schemas.ops import OpsActorContext

        self.now = datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc)
        self.actor_id = uuid4()
        self.actor = OpsActorContext(
            actor_type=ActorType.OPS,
            actor_id=self.actor_id,
            reason="Ops resolved reconciliation.",
        )

    def test_create_payment_evidence_classifies_match_mismatch_and_late_success(self) -> None:
        from app.models.enums import PaymentStatus, ReconciliationStatus
        from app.services.reconciliation_service import create_payment_evidence

        cases = (
            (
                _payment(status=PaymentStatus.SUCCESS, amount="100000.00"),
                "SUCCESS",
                Decimal("100000.00"),
                ReconciliationStatus.MATCHED,
                None,
            ),
            (
                _payment(status=PaymentStatus.SUCCESS, amount="100000.00"),
                "SUCCESS",
                Decimal("90000.00"),
                ReconciliationStatus.MISMATCHED,
                "AMOUNT_MISMATCH",
            ),
            (
                _payment(status=PaymentStatus.PENDING, amount="100000.00"),
                "SUCCESS",
                Decimal("100000.00"),
                ReconciliationStatus.MISMATCHED,
                "STATUS_MISMATCH",
            ),
            (
                _payment(status=PaymentStatus.EXPIRED, amount="100000.00"),
                "SUCCESS",
                Decimal("100000.00"),
                ReconciliationStatus.PENDING_REVIEW,
                "LATE_SUCCESS_AFTER_EXPIRATION",
            ),
        )

        for payment, external_status, external_amount, expected_result, expected_reason in cases:
            with self.subTest(expected_result=expected_result.value, reason=expected_reason):
                store = _ReconciliationStore()
                with store.patched_repositories():
                    record = create_payment_evidence(
                        _FakeDb(),
                        payment,
                        external_status=external_status,
                        external_amount=external_amount,
                        now=self.now,
                    )

                self.assertEqual(record.match_result, expected_result)
                self.assertEqual(record.mismatch_reason_code, expected_reason)

    def test_create_refund_evidence_classifies_match_amount_mismatch_and_status_conflict(self) -> None:
        from app.models.enums import ReconciliationStatus, RefundStatus
        from app.services.reconciliation_service import create_refund_evidence

        cases = (
            (
                _refund(status=RefundStatus.REFUNDED, amount="50000.00"),
                "SUCCESS",
                Decimal("50000.00"),
                ReconciliationStatus.MATCHED,
                None,
            ),
            (
                _refund(status=RefundStatus.REFUNDED, amount="50000.00"),
                "SUCCESS",
                Decimal("40000.00"),
                ReconciliationStatus.MISMATCHED,
                "AMOUNT_MISMATCH",
            ),
            (
                _refund(status=RefundStatus.REFUND_PENDING, amount="50000.00"),
                "SUCCESS",
                Decimal("50000.00"),
                ReconciliationStatus.PENDING_REVIEW,
                "STATUS_CONFLICT",
            ),
        )

        for refund, external_status, external_amount, expected_result, expected_reason in cases:
            with self.subTest(expected_result=expected_result.value, reason=expected_reason):
                store = _ReconciliationStore()
                with store.patched_repositories():
                    record = create_refund_evidence(
                        _FakeDb(),
                        refund,
                        external_status=external_status,
                        external_amount=external_amount,
                        now=self.now,
                    )

                self.assertEqual(record.match_result, expected_result)
                self.assertEqual(record.mismatch_reason_code, expected_reason)

    def test_resolve_record_updates_review_fields_and_records_audit(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import EntityType, ReconciliationStatus
        from app.schemas.reconciliation import ResolveReconciliationRequest
        from app.services.reconciliation_service import resolve_record

        missing_store = _ReconciliationStore(records=[])
        with missing_store.patched_repositories():
            with self.assertRaises(AppError) as error:
                resolve_record(
                    _FakeDb(),
                    uuid4(),
                    ResolveReconciliationRequest(actor=self.actor, review_note="Accepted."),
                    self.actor,
                    now=self.now,
                )
        self.assertEqual(error.exception.error_code, "RECONCILIATION_NOT_FOUND")

        resolved = _reconciliation_record(match_result=ReconciliationStatus.RESOLVED)
        resolved_store = _ReconciliationStore(records=[resolved])
        with resolved_store.patched_repositories():
            with self.assertRaises(AppError) as error:
                resolve_record(
                    _FakeDb(),
                    resolved.id,
                    ResolveReconciliationRequest(actor=self.actor, review_note="Accepted."),
                    self.actor,
                    now=self.now,
                )
        self.assertEqual(error.exception.error_code, "RECONCILIATION_ALREADY_RESOLVED")

        record = _reconciliation_record(match_result=ReconciliationStatus.MISMATCHED)
        db = _FakeDb()
        store = _ReconciliationStore(records=[record])

        with store.patched_repositories():
            response = resolve_record(
                db,
                record.id,
                ResolveReconciliationRequest(actor=self.actor, review_note="Provider evidence accepted."),
                self.actor,
                now=self.now,
            )

        self.assertTrue(db.committed)
        self.assertEqual(record.match_result, ReconciliationStatus.RESOLVED)
        self.assertEqual(record.reviewed_by, self.actor_id)
        self.assertEqual(record.review_note, "Provider evidence accepted.")
        self.assertEqual(response.match_result, ReconciliationStatus.RESOLVED)
        audit = db.audit_logs[0]
        self.assertEqual(audit.event_type, "RECONCILIATION_RESOLVED")
        self.assertEqual(audit.entity_type, EntityType.RECONCILIATION)
        self.assertEqual(audit.actor_id, self.actor_id)


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

    @property
    def audit_logs(self):
        from app.models.audit_log import AuditLog

        return [item for item in self.added if isinstance(item, AuditLog)]


class _ReconciliationStore:
    def __init__(self, records=None) -> None:
        self.records = records or []

    def patched_repositories(self):
        return _PatchGroup(
            patch(
                "app.services.reconciliation_service.reconciliation_repository.create_payment_reconciliation_record",
                side_effect=self.create_payment_reconciliation_record,
            ),
            patch(
                "app.services.reconciliation_service.reconciliation_repository.create_refund_reconciliation_record",
                side_effect=self.create_refund_reconciliation_record,
            ),
            patch(
                "app.services.reconciliation_service.reconciliation_repository.get_by_id",
                side_effect=self.get_by_id,
            ),
            patch(
                "app.services.reconciliation_service.reconciliation_repository.find",
                side_effect=self.find,
            ),
            patch(
                "app.services.reconciliation_service.reconciliation_repository.save",
                side_effect=self.save,
            ),
        )

    def create_payment_reconciliation_record(self, db, **kwargs):
        record = _reconciliation_record(
            entity_type="PAYMENT",
            entity_id=kwargs["payment"].id,
            internal_status=kwargs["payment"].status.value,
            external_status=kwargs["external_status"],
            internal_amount=kwargs["payment"].amount,
            external_amount=kwargs["external_amount"],
            match_result=kwargs["match_result"],
            mismatch_reason_code=kwargs.get("mismatch_reason_code"),
            mismatch_reason_message=kwargs.get("mismatch_reason_message"),
        )
        self.records.append(record)
        return record

    def create_refund_reconciliation_record(self, db, **kwargs):
        record = _reconciliation_record(
            entity_type="REFUND",
            entity_id=kwargs["refund"].id,
            internal_status=kwargs["refund"].status.value,
            external_status=kwargs["external_status"],
            internal_amount=kwargs["refund"].refund_amount,
            external_amount=kwargs["external_amount"],
            match_result=kwargs["match_result"],
            mismatch_reason_code=kwargs.get("mismatch_reason_code"),
            mismatch_reason_message=kwargs.get("mismatch_reason_message"),
        )
        self.records.append(record)
        return record

    def get_by_id(self, db, record_id):
        for record in self.records:
            if record.id == record_id:
                return record
        return None

    def find(self, db, match_result=None, entity_type=None, entity_id=None, limit=100):
        records = self.records
        if match_result is not None:
            records = [record for record in records if record.match_result == match_result]
        if entity_type is not None:
            records = [record for record in records if record.entity_type == entity_type]
        if entity_id is not None:
            records = [record for record in records if record.entity_id == entity_id]
        return records[:limit]

    def save(self, db, record):
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


def _payment(status, amount):
    from app.models.payment_transaction import PaymentTransaction

    return PaymentTransaction(
        id=uuid4(),
        transaction_id="pay_123",
        merchant_db_id=uuid4(),
        order_reference_id=uuid4(),
        order_id="ORDER-1001",
        amount=Decimal(amount),
        currency="VND",
        description="Demo QR payment",
        status=status,
        qr_content="MINI_GATEWAY|...",
        expire_at=datetime(2026, 5, 1, 10, 15, tzinfo=timezone.utc),
    )


def _refund(status, amount):
    from app.models.refund_transaction import RefundTransaction

    return RefundTransaction(
        id=uuid4(),
        refund_transaction_id="rfnd_123",
        merchant_db_id=uuid4(),
        payment_transaction_id=uuid4(),
        refund_id="REF-1001",
        refund_amount=Decimal(amount),
        reason="Customer requested refund",
        status=status,
    )


def _reconciliation_record(
    match_result,
    entity_type="PAYMENT",
    entity_id=None,
    internal_status="PENDING",
    external_status="SUCCESS",
    internal_amount=Decimal("100000.00"),
    external_amount=Decimal("100000.00"),
    mismatch_reason_code=None,
    mismatch_reason_message=None,
):
    from app.models.enums import EntityType
    from app.models.reconciliation_record import ReconciliationRecord

    return ReconciliationRecord(
        id=uuid4(),
        entity_type=EntityType(entity_type),
        entity_id=entity_id or uuid4(),
        internal_status=internal_status,
        external_status=external_status,
        internal_amount=internal_amount,
        external_amount=external_amount,
        match_result=match_result,
        mismatch_reason_code=mismatch_reason_code,
        mismatch_reason_message=mismatch_reason_message,
    )


if __name__ == "__main__":
    unittest.main()
