import unittest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


class PaymentStateMachineTest(unittest.TestCase):
    def test_mark_success_updates_pending_payment(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.payment_state_machine import mark_success

        payment = _payment(status=PaymentStatus.PENDING)
        paid_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)

        mark_success(payment, paid_at=paid_at, external_reference="bank-ref-1001")

        self.assertEqual(payment.status, PaymentStatus.SUCCESS)
        self.assertEqual(payment.paid_at, paid_at)
        self.assertEqual(payment.external_reference, "bank-ref-1001")

    def test_mark_failed_updates_pending_payment(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.payment_state_machine import mark_failed

        payment = _payment(status=PaymentStatus.PENDING)

        mark_failed(
            payment,
            reason_code="BANK_REJECTED",
            reason_message="Bank rejected payment.",
            external_reference="bank-ref-1001",
        )

        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(payment.failed_reason_code, "BANK_REJECTED")
        self.assertEqual(payment.failed_reason_message, "Bank rejected payment.")
        self.assertEqual(payment.external_reference, "bank-ref-1001")

    def test_mark_expired_updates_pending_payment(self) -> None:
        from app.models.enums import PaymentStatus
        from app.services.payment_state_machine import mark_expired

        payment = _payment(status=PaymentStatus.PENDING)

        mark_expired(payment)

        self.assertEqual(payment.status, PaymentStatus.EXPIRED)

    def test_rejects_invalid_final_state_transitions(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import PaymentStatus
        from app.services.payment_state_machine import mark_failed, mark_success

        paid_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)

        with self.assertRaises(AppError) as expired_to_success:
            mark_success(_payment(status=PaymentStatus.EXPIRED), paid_at=paid_at)
        self.assertEqual(expired_to_success.exception.error_code, "PAYMENT_INVALID_STATE_TRANSITION")
        self.assertEqual(expired_to_success.exception.status_code, 409)

        with self.assertRaises(AppError):
            mark_failed(_payment(status=PaymentStatus.SUCCESS), "FAILED", "Conflict.")

        with self.assertRaises(AppError):
            mark_success(_payment(status=PaymentStatus.FAILED), paid_at=paid_at)


def _payment(status):
    from app.models.payment_transaction import PaymentTransaction

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


if __name__ == "__main__":
    unittest.main()
