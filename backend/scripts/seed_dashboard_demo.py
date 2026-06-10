from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.internal_auth import hash_password
from app.db.session import SessionLocal
from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import (
    CallbackProcessingResult,
    CallbackSourceType,
    CallbackType,
    CredentialStatus,
    DeliveryAttemptResult,
    EntityType,
    MerchantStatus,
    MerchantUserRole,
    MerchantUserStatus,
    OnboardingCaseStatus,
    PaymentStatus,
    RefundStatus,
    WebhookEventStatus,
)
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_onboarding_case import MerchantOnboardingCase
from app.models.merchant_user import MerchantUser
from app.models.order_reference import OrderReference
from app.models.payment_transaction import PaymentTransaction
from app.models.refund_transaction import RefundTransaction
from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.models.webhook_event import WebhookEvent


MERCHANT_ID = os.getenv("DASHBOARD_DEMO_MERCHANT_ID", "m_demo_dashboard")
MERCHANT_EMAIL = os.getenv("DASHBOARD_DEMO_MERCHANT_EMAIL", "merchant.demo@example.com")
MERCHANT_PASSWORD = os.getenv("DASHBOARD_DEMO_MERCHANT_PASSWORD", "MerchantDemo123!")


def main() -> None:
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        merchant = _upsert_merchant(db)
        _upsert_onboarding_case(db, merchant)
        _upsert_credential(db, merchant)
        _upsert_merchant_user(db, merchant)

        payments = [
            _upsert_payment(
                db,
                merchant,
                transaction_id="pay_demo_001",
                order_id="ORDER-DEMO-001",
                amount=Decimal("125000.00"),
                description="Demo paid order",
                status=PaymentStatus.SUCCESS,
                created_at=now - timedelta(hours=3),
                expire_at=now + timedelta(hours=21),
                paid_at=now - timedelta(hours=2, minutes=55),
                external_reference="bank-demo-pay-001",
            ),
            _upsert_payment(
                db,
                merchant,
                transaction_id="pay_demo_002",
                order_id="ORDER-DEMO-002",
                amount=Decimal("999000.00"),
                description="Demo settled invoice",
                status=PaymentStatus.SUCCESS,
                created_at=now - timedelta(days=1, hours=2),
                expire_at=now - timedelta(hours=2),
                paid_at=now - timedelta(days=1, hours=1, minutes=55),
                external_reference="bank-demo-pay-002",
            ),
            _upsert_payment(
                db,
                merchant,
                transaction_id="pay_demo_003",
                order_id="ORDER-DEMO-003",
                amount=Decimal("450000.00"),
                description="Demo pending checkout",
                status=PaymentStatus.PENDING,
                created_at=now - timedelta(minutes=38),
                expire_at=now + timedelta(minutes=22),
                paid_at=None,
                external_reference=None,
            ),
            _upsert_payment(
                db,
                merchant,
                transaction_id="pay_demo_004",
                order_id="ORDER-DEMO-004",
                amount=Decimal("320000.00"),
                description="Demo failed payment",
                status=PaymentStatus.FAILED,
                created_at=now - timedelta(days=2, hours=4),
                expire_at=now - timedelta(days=2, hours=3),
                paid_at=None,
                external_reference="bank-demo-pay-004",
                failed_reason_code="BANK_DECLINED",
                failed_reason_message="Provider declined the transaction.",
            ),
            _upsert_payment(
                db,
                merchant,
                transaction_id="pay_demo_005",
                order_id="ORDER-DEMO-005",
                amount=Decimal("780000.00"),
                description="Demo expired checkout",
                status=PaymentStatus.EXPIRED,
                created_at=now - timedelta(days=4),
                expire_at=now - timedelta(days=3, hours=23),
                paid_at=None,
                external_reference=None,
                failed_reason_code="PAYMENT_EXPIRED",
                failed_reason_message="Payment expired before provider confirmation.",
            ),
        ]

        refund = _upsert_refund(db, merchant, payments[0], now)
        _replace_callback_logs(db, payments[0], refund, now)
        _upsert_webhooks(db, merchant, payments[0], refund, now)

        db.commit()

    print("Dashboard demo data is ready.")
    print(f"Merchant id: {MERCHANT_ID}")
    print(f"Portal user: {MERCHANT_EMAIL}")
    print("Portal password was set from DASHBOARD_DEMO_MERCHANT_PASSWORD or the local demo default.")


def _upsert_merchant(db, *, merchant_id: str = MERCHANT_ID) -> Merchant:
    merchant = db.scalar(select(Merchant).where(Merchant.merchant_id == merchant_id))
    if merchant is None:
        merchant = Merchant(merchant_id=merchant_id)
        db.add(merchant)
    merchant.merchant_name = "Demo Merchant Dashboard"
    merchant.legal_name = "Demo Merchant Dashboard Co., Ltd."
    merchant.contact_name = "Demo Merchant Owner"
    merchant.contact_email = "merchant.demo@example.com"
    merchant.contact_phone = "+84900000000"
    merchant.webhook_url = "https://merchant-demo.example.com/webhooks/payment-gateway"
    merchant.allowed_ip_list = ["127.0.0.1"]
    merchant.status = MerchantStatus.ACTIVE
    merchant.settlement_account_name = "Demo Merchant Dashboard"
    merchant.settlement_account_number = "9704000000000001"
    merchant.settlement_bank_code = "DEMO"
    db.flush()
    return merchant


def _upsert_onboarding_case(db, merchant: Merchant) -> MerchantOnboardingCase:
    onboarding = db.scalar(
        select(MerchantOnboardingCase).where(MerchantOnboardingCase.merchant_db_id == merchant.id)
    )
    if onboarding is None:
        onboarding = MerchantOnboardingCase(merchant_db_id=merchant.id)
        db.add(onboarding)
    onboarding.status = OnboardingCaseStatus.APPROVED
    onboarding.domain_or_app_name = "Demo Storefront"
    onboarding.submitted_profile_json = {
        "business_model": "Sandbox ecommerce",
        "monthly_volume": "demo",
    }
    onboarding.documents_json = {
        "business_license": "demo-business-license.pdf",
        "bank_account": "demo-bank-account.pdf",
    }
    onboarding.review_checks_json = {
        "kyb": "passed",
        "risk": "low",
        "dashboard_demo": True,
    }
    onboarding.decision_note = "Demo merchant approved for dashboard sandbox data."
    onboarding.reviewed_at = datetime.now(timezone.utc)
    db.flush()
    return onboarding


def _upsert_credential(db, merchant: Merchant) -> MerchantCredential:
    credential = db.scalar(
        select(MerchantCredential).where(MerchantCredential.access_key == "ak_demo_dashboard")
    )
    if credential is None:
        credential = MerchantCredential(
            merchant_db_id=merchant.id,
            access_key="ak_demo_dashboard",
        )
        db.add(credential)
    credential.merchant_db_id = merchant.id
    credential.secret_key_encrypted = "demo-secret-placeholder-not-for-real-payments"
    credential.secret_key_last4 = "demo"
    credential.status = CredentialStatus.ACTIVE
    credential.expired_at = None
    credential.rotated_at = datetime.now(timezone.utc) - timedelta(days=7)
    db.flush()
    return credential


def _upsert_merchant_user(db, merchant: Merchant) -> MerchantUser:
    user = db.scalar(
        select(MerchantUser).where(
            MerchantUser.merchant_db_id == merchant.id,
            MerchantUser.email == MERCHANT_EMAIL,
        )
    )
    if user is None:
        user = MerchantUser(
            merchant_db_id=merchant.id,
            email=MERCHANT_EMAIL,
        )
        db.add(user)
    user.full_name = "Demo Merchant Admin"
    user.role = MerchantUserRole.MERCHANT_ADMIN
    user.status = MerchantUserStatus.ACTIVE
    user.password_hash = hash_password(MERCHANT_PASSWORD)
    db.flush()
    return user


def _upsert_payment(
    db,
    merchant: Merchant,
    *,
    transaction_id: str,
    order_id: str,
    amount: Decimal,
    description: str,
    status: PaymentStatus,
    created_at: datetime,
    expire_at: datetime,
    paid_at: datetime | None,
    external_reference: str | None,
    failed_reason_code: str | None = None,
    failed_reason_message: str | None = None,
) -> PaymentTransaction:
    order_ref = db.scalar(
        select(OrderReference).where(
            OrderReference.merchant_db_id == merchant.id,
            OrderReference.order_id == order_id,
        )
    )
    if order_ref is None:
        order_ref = OrderReference(
            merchant_db_id=merchant.id,
            order_id=order_id,
        )
        db.add(order_ref)
        db.flush()

    payment = db.scalar(
        select(PaymentTransaction).where(PaymentTransaction.transaction_id == transaction_id)
    )
    if payment is None:
        payment = PaymentTransaction(
            transaction_id=transaction_id,
            merchant_db_id=merchant.id,
            order_reference_id=order_ref.id,
            order_id=order_id,
        )
        db.add(payment)
    payment.amount = amount
    payment.currency = "VND"
    payment.description = description
    payment.status = status
    payment.qr_content = f"DEMOQR|{MERCHANT_ID}|{order_id}|{amount}"
    payment.qr_image_url = None
    payment.qr_image_base64 = None
    payment.external_reference = external_reference
    payment.idempotency_key = f"demo-{transaction_id}"
    payment.expire_at = expire_at
    payment.paid_at = paid_at
    payment.failed_reason_code = failed_reason_code
    payment.failed_reason_message = failed_reason_message
    payment.created_at = created_at
    payment.updated_at = created_at
    db.flush()
    order_ref.latest_payment_transaction_id = payment.id
    order_ref.order_status_snapshot = status.value
    db.flush()
    return payment


def _upsert_refund(
    db,
    merchant: Merchant,
    payment: PaymentTransaction,
    now: datetime,
) -> RefundTransaction:
    refund = db.scalar(
        select(RefundTransaction).where(RefundTransaction.refund_transaction_id == "rfnd_demo_001")
    )
    if refund is None:
        refund = RefundTransaction(
            refund_transaction_id="rfnd_demo_001",
            merchant_db_id=merchant.id,
            payment_transaction_id=payment.id,
            refund_id="REF-DEMO-001",
        )
        db.add(refund)
    refund.refund_amount = payment.amount
    refund.reason = "Customer requested cancellation in demo flow."
    refund.status = RefundStatus.REFUNDED
    refund.external_reference = "bank-demo-refund-001"
    refund.idempotency_key = "demo-rfnd_demo_001"
    refund.processed_at = now - timedelta(hours=1, minutes=35)
    refund.failed_reason_code = None
    refund.failed_reason_message = None
    refund.created_at = now - timedelta(hours=1, minutes=40)
    refund.updated_at = now - timedelta(hours=1, minutes=35)
    db.flush()
    return refund


def _replace_callback_logs(
    db,
    payment: PaymentTransaction,
    refund: RefundTransaction,
    now: datetime,
) -> None:
    references = [payment.transaction_id, refund.refund_transaction_id]
    db.execute(delete(BankCallbackLog).where(BankCallbackLog.transaction_reference.in_(references)))
    db.add_all(
        [
            BankCallbackLog(
                source_type=CallbackSourceType.SIMULATOR,
                external_reference=payment.external_reference,
                transaction_reference=payment.transaction_id,
                callback_type=CallbackType.PAYMENT_RESULT,
                raw_payload_json={
                    "transaction_id": payment.transaction_id,
                    "status": "SUCCESS",
                    "amount": str(payment.amount),
                },
                normalized_status=PaymentStatus.SUCCESS.value,
                received_at=now - timedelta(hours=2, minutes=55),
                processed_at=now - timedelta(hours=2, minutes=54),
                processing_result=CallbackProcessingResult.PROCESSED,
                error_message=None,
            ),
            BankCallbackLog(
                source_type=CallbackSourceType.SIMULATOR,
                external_reference=refund.external_reference,
                transaction_reference=refund.refund_transaction_id,
                callback_type=CallbackType.REFUND_RESULT,
                raw_payload_json={
                    "refund_transaction_id": refund.refund_transaction_id,
                    "status": "REFUNDED",
                    "amount": str(refund.refund_amount),
                },
                normalized_status=RefundStatus.REFUNDED.value,
                received_at=now - timedelta(hours=1, minutes=35),
                processed_at=now - timedelta(hours=1, minutes=34),
                processing_result=CallbackProcessingResult.PROCESSED,
                error_message=None,
            ),
        ]
    )
    db.flush()


def _upsert_webhooks(
    db,
    merchant: Merchant,
    payment: PaymentTransaction,
    refund: RefundTransaction,
    now: datetime,
) -> None:
    payment_event = _upsert_webhook_event(
        db,
        merchant,
        event_id="wh_demo_pay_001",
        event_type="payment.succeeded",
        entity_type=EntityType.PAYMENT,
        entity_id=payment.id,
        payload_json={
            "event_type": "payment.succeeded",
            "transaction_id": payment.transaction_id,
            "order_id": payment.order_id,
            "status": payment.status.value,
            "amount": str(payment.amount),
        },
        status=WebhookEventStatus.DELIVERED,
        attempt_count=1,
        created_at=now - timedelta(hours=2, minutes=50),
        next_retry_at=None,
        last_attempt_at=now - timedelta(hours=2, minutes=49),
    )
    refund_event = _upsert_webhook_event(
        db,
        merchant,
        event_id="wh_demo_refund_001",
        event_type="refund.refunded",
        entity_type=EntityType.REFUND,
        entity_id=refund.id,
        payload_json={
            "event_type": "refund.refunded",
            "refund_transaction_id": refund.refund_transaction_id,
            "refund_id": refund.refund_id,
            "status": refund.status.value,
            "amount": str(refund.refund_amount),
        },
        status=WebhookEventStatus.FAILED,
        attempt_count=2,
        created_at=now - timedelta(hours=1, minutes=30),
        next_retry_at=now + timedelta(minutes=30),
        last_attempt_at=now - timedelta(minutes=10),
    )

    db.execute(
        delete(WebhookDeliveryAttempt).where(
            WebhookDeliveryAttempt.webhook_event_id.in_([payment_event.id, refund_event.id])
        )
    )
    db.add_all(
        [
            WebhookDeliveryAttempt(
                webhook_event_id=payment_event.id,
                attempt_no=1,
                request_url="https://merchant-demo.example.com/webhooks/payment-gateway",
                request_headers_json={"x-demo-signature": "delivered"},
                request_body_json=payment_event.payload_json,
                response_status_code=200,
                response_body_snippet="ok",
                error_message=None,
                started_at=now - timedelta(hours=2, minutes=49),
                finished_at=now - timedelta(hours=2, minutes=49, seconds=-1),
                result=DeliveryAttemptResult.SUCCESS,
            ),
            WebhookDeliveryAttempt(
                webhook_event_id=refund_event.id,
                attempt_no=1,
                request_url="https://merchant-demo.example.com/webhooks/payment-gateway",
                request_headers_json={"x-demo-signature": "failed-1"},
                request_body_json=refund_event.payload_json,
                response_status_code=500,
                response_body_snippet="temporary upstream error",
                error_message=None,
                started_at=now - timedelta(minutes=20),
                finished_at=now - timedelta(minutes=20, seconds=-2),
                result=DeliveryAttemptResult.FAILED,
            ),
            WebhookDeliveryAttempt(
                webhook_event_id=refund_event.id,
                attempt_no=2,
                request_url="https://merchant-demo.example.com/webhooks/payment-gateway",
                request_headers_json={"x-demo-signature": "failed-2"},
                request_body_json=refund_event.payload_json,
                response_status_code=None,
                response_body_snippet=None,
                error_message="Connection timed out after 5 seconds.",
                started_at=now - timedelta(minutes=10),
                finished_at=now - timedelta(minutes=10, seconds=-5),
                result=DeliveryAttemptResult.TIMEOUT,
            ),
        ]
    )
    db.flush()


def _upsert_webhook_event(
    db,
    merchant: Merchant,
    *,
    event_id: str,
    event_type: str,
    entity_type: EntityType,
    entity_id,
    payload_json: dict,
    status: WebhookEventStatus,
    attempt_count: int,
    created_at: datetime,
    next_retry_at: datetime | None,
    last_attempt_at: datetime | None,
) -> WebhookEvent:
    event = db.scalar(select(WebhookEvent).where(WebhookEvent.event_id == event_id))
    if event is None:
        event = WebhookEvent(
            event_id=event_id,
            merchant_db_id=merchant.id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        db.add(event)
    event.event_type = event_type
    event.payload_json = payload_json
    event.signature = f"sha256=demo-{event_id}"
    event.status = status
    event.next_retry_at = next_retry_at
    event.attempt_count = attempt_count
    event.last_attempt_at = last_attempt_at
    event.created_at = created_at
    event.updated_at = created_at
    db.flush()
    return event


if __name__ == "__main__":
    main()
