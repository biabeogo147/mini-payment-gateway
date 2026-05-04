import unittest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4


class RefundStateMachineTest(unittest.TestCase):
    def test_mark_refunded_updates_pending_refund(self) -> None:
        from app.models.enums import RefundStatus
        from app.services.refund_state_machine import mark_refunded

        processed_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)
        refund = _refund(status=RefundStatus.REFUND_PENDING)

        mark_refunded(refund, processed_at=processed_at, external_reference="bank-refund-1001")

        self.assertEqual(refund.status, RefundStatus.REFUNDED)
        self.assertEqual(refund.processed_at, processed_at)
        self.assertEqual(refund.external_reference, "bank-refund-1001")

    def test_mark_refund_failed_updates_pending_refund(self) -> None:
        from app.models.enums import RefundStatus
        from app.services.refund_state_machine import mark_refund_failed

        processed_at = datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc)
        refund = _refund(status=RefundStatus.REFUND_PENDING)

        mark_refund_failed(
            refund,
            reason_code="BANK_REJECTED",
            reason_message="Bank rejected refund.",
            external_reference="bank-refund-1001",
            processed_at=processed_at,
        )

        self.assertEqual(refund.status, RefundStatus.REFUND_FAILED)
        self.assertEqual(refund.failed_reason_code, "BANK_REJECTED")
        self.assertEqual(refund.failed_reason_message, "Bank rejected refund.")
        self.assertEqual(refund.processed_at, processed_at)
        self.assertEqual(refund.external_reference, "bank-refund-1001")

    def test_rejects_invalid_final_state_transitions(self) -> None:
        from app.core.errors import AppError
        from app.models.enums import RefundStatus
        from app.services.refund_state_machine import mark_refund_failed, mark_refunded

        rejected_cases = (
            (RefundStatus.REFUNDED, mark_refund_failed),
            (RefundStatus.REFUND_FAILED, mark_refunded),
            (RefundStatus.REFUNDED, mark_refunded),
        )

        for current_status, transition in rejected_cases:
            with self.subTest(current_status=current_status.value, transition=transition.__name__):
                refund = _refund(status=current_status)
                with self.assertRaises(AppError) as error:
                    if transition is mark_refund_failed:
                        transition(
                            refund,
                            reason_code="BANK_REJECTED",
                            reason_message=None,
                            processed_at=datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc),
                        )
                    else:
                        transition(
                            refund,
                            processed_at=datetime(2026, 4, 29, 10, 5, tzinfo=timezone.utc),
                        )

                self.assertEqual(error.exception.error_code, "REFUND_INVALID_STATE_TRANSITION")
                self.assertEqual(error.exception.status_code, 409)


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
