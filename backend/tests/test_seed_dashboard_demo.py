import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from app.models.enums import PaymentStatus
from scripts import seed_dashboard_demo


class SeedDashboardDemoTest(unittest.TestCase):
    def test_upsert_payment_generates_vietqr_demo_payload_with_keyword_arguments(self) -> None:
        db = _FakeDb()
        merchant = SimpleNamespace(id=uuid4())
        qr_account = SimpleNamespace(account_number="9704000000000001")

        def fake_generate_vietqr_payment_qr(*, qr_account, amount, qr_reference):
            return SimpleNamespace(
                qr_content=f"000201|{qr_reference}|{amount}|{qr_account.account_number}",
                qr_image_base64="data:image/png;base64,demo",
            )

        with patch.object(
            seed_dashboard_demo,
            "generate_vietqr_payment_qr",
            side_effect=fake_generate_vietqr_payment_qr,
        ):
            payment = seed_dashboard_demo._upsert_payment(
                db,
                merchant,
                qr_account,
                transaction_id="pay_demo_001",
                order_id="ORDER-DEMO-001",
                amount=Decimal("125000.00"),
                status=PaymentStatus.PENDING,
                description="Demo payment",
                expire_at=datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc),
                paid_at=None,
                external_reference=None,
                failed_reason_code=None,
                failed_reason_message=None,
                created_at=datetime(2026, 6, 16, 9, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(payment.qr_reference, "PDEMO001")
        self.assertTrue(payment.qr_content.startswith("000201|PDEMO001|"))
        self.assertEqual(payment.qr_image_base64, "data:image/png;base64,demo")


class _FakeDb:
    def scalar(self, _statement):
        return None

    def add(self, _model) -> None:
        return None

    def flush(self) -> None:
        return None


if __name__ == "__main__":
    unittest.main()
