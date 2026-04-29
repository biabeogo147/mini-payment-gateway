import unittest
from uuid import uuid4

from app.core.errors import AppError
from app.models.enums import MerchantStatus
from app.models.merchant import Merchant


class MerchantReadinessTest(unittest.TestCase):
    def test_active_merchant_can_create_payment_and_refund(self) -> None:
        from app.services.merchant_readiness_service import assert_can_create_payment, assert_can_create_refund

        merchant = self._merchant(MerchantStatus.ACTIVE)

        self.assertIsNone(assert_can_create_payment(merchant))
        self.assertIsNone(assert_can_create_refund(merchant))

    def test_non_active_merchant_cannot_create_payment_or_refund(self) -> None:
        from app.services.merchant_readiness_service import assert_can_create_payment, assert_can_create_refund

        for status in (
            MerchantStatus.PENDING_REVIEW,
            MerchantStatus.REJECTED,
            MerchantStatus.SUSPENDED,
            MerchantStatus.DISABLED,
        ):
            with self.subTest(status=status.value):
                merchant = self._merchant(status)

                with self.assertRaises(AppError) as payment_error:
                    assert_can_create_payment(merchant)
                with self.assertRaises(AppError) as refund_error:
                    assert_can_create_refund(merchant)

                self.assertEqual(payment_error.exception.error_code, "MERCHANT_NOT_ACTIVE")
                self.assertEqual(refund_error.exception.error_code, "MERCHANT_NOT_ACTIVE")
                self.assertEqual(payment_error.exception.status_code, 403)
                self.assertEqual(payment_error.exception.details, {"merchant_status": status.value})

    def test_ops_can_inspect_suspended_merchant(self) -> None:
        from app.services.merchant_readiness_service import assert_can_receive_ops_update

        merchant = self._merchant(MerchantStatus.SUSPENDED)

        self.assertIsNone(assert_can_receive_ops_update(merchant))

    @staticmethod
    def _merchant(status: MerchantStatus) -> Merchant:
        return Merchant(
            id=uuid4(),
            merchant_id=f"m_{status.value.lower()}",
            merchant_name="Demo Merchant",
            contact_email="ops@example.com",
            status=status,
        )


if __name__ == "__main__":
    unittest.main()
