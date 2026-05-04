import json
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import delete, or_, select, update

from app.core.security import sha256_hex, sign_hmac_sha256
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.bank_callback_log import BankCallbackLog
from app.models.enums import (
    DeliveryAttemptResult,
    InternalUserRole,
    InternalUserStatus,
    PaymentStatus,
    ReconciliationStatus,
    RefundStatus,
    WebhookEventStatus,
)
from app.models.internal_user import InternalUser
from app.models.merchant import Merchant
from app.models.merchant_credential import MerchantCredential
from app.models.merchant_onboarding_case import MerchantOnboardingCase
from app.models.order_reference import OrderReference
from app.models.payment_transaction import PaymentTransaction
from app.models.reconciliation_record import ReconciliationRecord
from app.models.refund_transaction import RefundTransaction
from app.models.webhook_delivery_attempt import WebhookDeliveryAttempt
from app.models.webhook_event import WebhookEvent
from app.services import expiration_service, webhook_delivery_service


def _compact_json(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


class _FakeResponse:
    def __init__(self, status_code: int, text: str = "ok"):
        self.status_code = status_code
        self.text = text


class _FakeHttpClient:
    def __init__(self, responses: list[_FakeResponse]):
        self.responses = responses
        self.requests: list[dict] = []

    def post(self, url: str, *, content: bytes, headers: dict, timeout: float):
        self.requests.append(
            {
                "url": url,
                "content": content,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


class PaymentRefundWebhookE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self._cleanup_e2e_data()
        self.addCleanup(self._cleanup_e2e_data)

    def _cleanup_e2e_data(self) -> None:
        with SessionLocal() as db:
            merchant_ids = list(
                db.scalars(select(Merchant.id).where(Merchant.merchant_id.like("m_e2e_%")))
            )
            user_ids = list(
                db.scalars(select(InternalUser.id).where(InternalUser.email.like("e2e-%@example.com")))
            )

            if not merchant_ids and not user_ids:
                return

            payment_ids = (
                list(
                    db.scalars(
                        select(PaymentTransaction.id).where(
                            PaymentTransaction.merchant_db_id.in_(merchant_ids)
                        )
                    )
                )
                if merchant_ids
                else []
            )
            payment_refs = (
                list(
                    db.scalars(
                        select(PaymentTransaction.transaction_id).where(
                            PaymentTransaction.merchant_db_id.in_(merchant_ids)
                        )
                    )
                )
                if merchant_ids
                else []
            )
            refund_ids = (
                list(
                    db.scalars(
                        select(RefundTransaction.id).where(
                            RefundTransaction.merchant_db_id.in_(merchant_ids)
                        )
                    )
                )
                if merchant_ids
                else []
            )
            refund_refs = (
                list(
                    db.scalars(
                        select(RefundTransaction.refund_transaction_id).where(
                            RefundTransaction.merchant_db_id.in_(merchant_ids)
                        )
                    )
                )
                if merchant_ids
                else []
            )
            webhook_ids = (
                list(
                    db.scalars(
                        select(WebhookEvent.id).where(WebhookEvent.merchant_db_id.in_(merchant_ids))
                    )
                )
                if merchant_ids
                else []
            )
            case_ids = (
                list(
                    db.scalars(
                        select(MerchantOnboardingCase.id).where(
                            MerchantOnboardingCase.merchant_db_id.in_(merchant_ids)
                        )
                    )
                )
                if merchant_ids
                else []
            )
            credential_ids = (
                list(
                    db.scalars(
                        select(MerchantCredential.id).where(
                            MerchantCredential.merchant_db_id.in_(merchant_ids)
                        )
                    )
                )
                if merchant_ids
                else []
            )
            reconciliation_ids = (
                list(
                    db.scalars(
                        select(ReconciliationRecord.id).where(
                            ReconciliationRecord.entity_id.in_(payment_ids + refund_ids)
                        )
                    )
                )
                if payment_ids or refund_ids
                else []
            )

            audit_entity_ids = (
                merchant_ids
                + payment_ids
                + refund_ids
                + webhook_ids
                + case_ids
                + credential_ids
                + reconciliation_ids
            )
            if user_ids and audit_entity_ids:
                db.execute(
                    delete(AuditLog).where(
                        or_(
                            AuditLog.actor_id.in_(user_ids),
                            AuditLog.entity_id.in_(audit_entity_ids),
                        )
                    )
                )
            elif user_ids:
                db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
            elif audit_entity_ids:
                db.execute(delete(AuditLog).where(AuditLog.entity_id.in_(audit_entity_ids)))

            if webhook_ids:
                db.execute(
                    delete(WebhookDeliveryAttempt).where(
                        WebhookDeliveryAttempt.webhook_event_id.in_(webhook_ids)
                    )
                )
                db.execute(delete(WebhookEvent).where(WebhookEvent.id.in_(webhook_ids)))

            callback_refs = payment_refs + refund_refs
            if callback_refs:
                db.execute(
                    delete(BankCallbackLog).where(
                        BankCallbackLog.transaction_reference.in_(callback_refs)
                    )
                )

            if reconciliation_ids:
                db.execute(
                    delete(ReconciliationRecord).where(
                        ReconciliationRecord.id.in_(reconciliation_ids)
                    )
                )

            if merchant_ids:
                db.execute(
                    update(OrderReference)
                    .where(OrderReference.merchant_db_id.in_(merchant_ids))
                    .values(latest_payment_transaction_id=None)
                )
                db.execute(
                    delete(RefundTransaction).where(
                        RefundTransaction.merchant_db_id.in_(merchant_ids)
                    )
                )
                db.execute(
                    delete(PaymentTransaction).where(
                        PaymentTransaction.merchant_db_id.in_(merchant_ids)
                    )
                )
                db.execute(
                    delete(OrderReference).where(OrderReference.merchant_db_id.in_(merchant_ids))
                )
                db.execute(
                    delete(MerchantOnboardingCase).where(
                        MerchantOnboardingCase.merchant_db_id.in_(merchant_ids)
                    )
                )
                db.execute(
                    delete(MerchantCredential).where(
                            MerchantCredential.merchant_db_id.in_(merchant_ids)
                    )
                )
                db.execute(delete(Merchant).where(Merchant.id.in_(merchant_ids)))

            if user_ids:
                db.execute(delete(InternalUser).where(InternalUser.id.in_(user_ids)))

            db.commit()

    def _create_ops_user(self, suffix: str):
        with SessionLocal() as db:
            user = InternalUser(
                email=f"e2e-{suffix}@example.com",
                full_name="E2E Ops",
                role=InternalUserRole.OPS,
                status=InternalUserStatus.ACTIVE,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id

    def _actor(self, ops_user_id, reason: str) -> dict:
        return {
            "actor": {
                "actor_type": "OPS",
                "actor_id": str(ops_user_id),
                "reason": reason,
            }
        }

    def _setup_active_merchant(self, suffix: str) -> dict:
        ops_user_id = self._create_ops_user(suffix)
        merchant_id = f"m_e2e_{suffix}"
        secret_key = f"e2e_secret_{suffix}"

        create_response = self.client.post(
            "/v1/ops/merchants",
            json={
                **self._actor(ops_user_id, "E2E create merchant"),
                "merchant_id": merchant_id,
                "merchant_name": f"E2E Merchant {suffix}",
                "legal_name": f"E2E Merchant Legal {suffix}",
                "contact_name": "E2E Contact",
                "contact_email": f"merchant-{suffix}@example.com",
                "webhook_url": f"https://merchant.example.com/e2e/{suffix}/webhook",
                "settlement_account_name": f"E2E Merchant {suffix}",
                "settlement_account_number": f"9704000000{suffix[:8]}",
                "settlement_bank_code": "VCB",
            },
        )
        self.assertEqual(create_response.status_code, 200, create_response.text)

        submit_response = self.client.put(
            f"/v1/ops/merchants/{merchant_id}/onboarding-case",
            json={
                **self._actor(ops_user_id, "E2E submit onboarding"),
                "domain_or_app_name": f"merchant-{suffix}.example.com",
                "submitted_profile_json": {
                    "registration_number": f"REG-{suffix}",
                    "business_category": "retail",
                    "settlement_bank_account": f"9704000000{suffix[:8]}",
                },
                "documents_json": {
                    "kyc": f"https://merchant.example.com/e2e/{suffix}/kyc.pdf",
                },
                "review_checks_json": {
                    "ownership_verified": True,
                    "sanctions_screening": "clear",
                },
            },
        )
        self.assertEqual(submit_response.status_code, 200, submit_response.text)

        approve_response = self.client.post(
            f"/v1/ops/merchants/{merchant_id}/onboarding-case/approve",
            json={
                **self._actor(ops_user_id, "E2E approve onboarding"),
                "reviewed_by": str(ops_user_id),
                "decision_note": "E2E approved",
            },
        )
        self.assertEqual(approve_response.status_code, 200, approve_response.text)

        credential_response = self.client.post(
            f"/v1/ops/merchants/{merchant_id}/credentials",
            json={
                **self._actor(ops_user_id, "E2E issue credential"),
                "access_key": f"ak_e2e_{suffix}",
                "secret_key": secret_key,
            },
        )
        self.assertEqual(credential_response.status_code, 200, credential_response.text)
        access_key = credential_response.json()["access_key"]

        activate_response = self.client.post(
            f"/v1/ops/merchants/{merchant_id}/activate",
            json=self._actor(ops_user_id, "E2E activate merchant"),
        )
        self.assertEqual(activate_response.status_code, 200, activate_response.text)

        return {
            "merchant_id": merchant_id,
            "access_key": access_key,
            "secret_key": secret_key,
            "ops_user_id": ops_user_id,
        }

    def _signed_headers(
        self,
        seed: dict,
        method: str,
        path: str,
        body: bytes,
        *,
        idempotency_key: str | None = None,
        secret_key: str | None = None,
    ) -> dict:
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        payload_hash = sha256_hex(body)
        signature_payload = f"{timestamp}.{method.upper()}.{path}.{payload_hash}"
        headers = {
            "Content-Type": "application/json",
            "X-Merchant-Id": seed["merchant_id"],
            "X-Access-Key": seed["access_key"],
            "X-Timestamp": timestamp,
            "X-Signature": sign_hmac_sha256(secret_key or seed["secret_key"], signature_payload),
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    def _merchant_post(
        self,
        seed: dict,
        path: str,
        payload: dict,
        *,
        idempotency_key: str | None = None,
        secret_key: str | None = None,
    ):
        body = _compact_json(payload)
        return self.client.post(
            path,
            content=body,
            headers=self._signed_headers(
                seed,
                "POST",
                path,
                body,
                idempotency_key=idempotency_key,
                secret_key=secret_key,
            ),
        )

    def _create_payment(self, seed: dict, suffix: str, amount: str = "12345.00"):
        path = "/v1/payments"
        payload = {
            "order_id": f"order-{suffix}",
            "amount": amount,
            "currency": "VND",
            "description": "E2E payment",
            "ttl_seconds": 900,
        }
        response = self._merchant_post(
            seed,
            path,
            payload,
            idempotency_key=f"pay-{suffix}",
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _mark_payment_success(self, transaction_id: str, amount: str = "12345.00"):
        response = self.client.post(
            "/v1/provider/callbacks/payment",
            json={
                "transaction_reference": transaction_id,
                "external_reference": f"bank-{transaction_id}",
                "status": "SUCCESS",
                "amount": amount,
                "paid_at": datetime.now(timezone.utc).isoformat(),
                "raw_payload": {
                    "provider": "BANK_SIM",
                    "transaction_reference": transaction_id,
                    "amount": amount,
                    "status": "SUCCESS",
                },
                "source_type": "SIMULATOR",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _create_refund(self, seed: dict, suffix: str, transaction_id: str, amount: str = "12345.00"):
        path = "/v1/refunds"
        payload = {
            "original_transaction_id": transaction_id,
            "refund_id": f"refund-{suffix}",
            "refund_amount": amount,
            "reason": "E2E refund",
        }
        response = self._merchant_post(
            seed,
            path,
            payload,
            idempotency_key=f"refund-{suffix}",
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _mark_refund_success(self, refund_transaction_id: str, amount: str = "12345.00"):
        response = self.client.post(
            "/v1/provider/callbacks/refund",
            json={
                "refund_transaction_id": refund_transaction_id,
                "external_reference": f"bank-{refund_transaction_id}",
                "status": "SUCCESS",
                "amount": amount,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "raw_payload": {
                    "provider": "BANK_SIM",
                    "refund_transaction_id": refund_transaction_id,
                    "amount": amount,
                    "status": "SUCCESS",
                },
                "source_type": "SIMULATOR",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _payment_row(self, transaction_id: str) -> PaymentTransaction:
        with SessionLocal() as db:
            row = db.scalar(
                select(PaymentTransaction).where(
                    PaymentTransaction.transaction_id == transaction_id
                )
            )
            self.assertIsNotNone(row)
            return row

    def _refund_row(self, refund_transaction_id: str) -> RefundTransaction:
        with SessionLocal() as db:
            row = db.scalar(
                select(RefundTransaction).where(
                    RefundTransaction.refund_transaction_id == refund_transaction_id
                )
            )
            self.assertIsNotNone(row)
            return row

    def _latest_event(self, event_type: str) -> WebhookEvent:
        with SessionLocal() as db:
            row = db.scalar(
                select(WebhookEvent)
                .where(WebhookEvent.event_type == event_type)
                .order_by(WebhookEvent.created_at.desc())
            )
            self.assertIsNotNone(row)
            return row

    def _deliver_event(self, event_id, status_code: int = 200):
        fake_client = _FakeHttpClient([_FakeResponse(status_code)])
        with SessionLocal() as db:
            event = db.get(WebhookEvent, event_id)
            self.assertIsNotNone(event)
            delivered = webhook_delivery_service.deliver_event(
                db,
                event,
                http_client=fake_client,
            )
            db.commit()
            db.refresh(event)
            return delivered, event, fake_client

    def test_happy_path_covers_onboarding_payment_refund_and_webhooks(self):
        suffix = uuid4().hex[:12]
        seed = self._setup_active_merchant(suffix)

        payment = self._create_payment(seed, suffix)
        payment_callback = self._mark_payment_success(payment["transaction_id"])
        self.assertEqual(payment_callback["processing_result"], "PROCESSED")
        self.assertEqual(self._payment_row(payment["transaction_id"]).status, PaymentStatus.SUCCESS)

        payment_event = self._latest_event("payment.succeeded")
        delivered, delivered_payment_event, fake_client = self._deliver_event(payment_event.id)
        self.assertTrue(delivered)
        self.assertEqual(delivered_payment_event.status, WebhookEventStatus.DELIVERED)
        self.assertEqual(len(fake_client.requests), 1)

        refund = self._create_refund(seed, suffix, payment["transaction_id"])
        refund_callback = self._mark_refund_success(refund["refund_transaction_id"])
        self.assertEqual(refund_callback["processing_result"], "PROCESSED")
        self.assertEqual(
            self._refund_row(refund["refund_transaction_id"]).status,
            RefundStatus.REFUNDED,
        )

        refund_event = self._latest_event("refund.succeeded")
        delivered, delivered_refund_event, _ = self._deliver_event(refund_event.id)
        self.assertTrue(delivered)
        self.assertEqual(delivered_refund_event.status, WebhookEventStatus.DELIVERED)

    def test_idempotent_payment_and_hmac_failure_are_explicit(self):
        suffix = uuid4().hex[:12]
        seed = self._setup_active_merchant(suffix)
        path = "/v1/payments"
        payload = {
            "order_id": f"order-{suffix}",
            "amount": "99000.00",
            "currency": "VND",
            "description": "E2E idempotency",
            "expire_at": (datetime.now(timezone.utc) + timedelta(minutes=15))
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        }

        first = self._merchant_post(seed, path, payload, idempotency_key=f"idem-{suffix}")
        second = self._merchant_post(seed, path, payload, idempotency_key=f"idem-{suffix}")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["transaction_id"], second.json()["transaction_id"])

        auth_failure = self._merchant_post(
            seed,
            path,
            {
                **payload,
                "order_id": f"bad-auth-{suffix}",
            },
            idempotency_key=f"bad-auth-{suffix}",
            secret_key="wrong-secret",
        )
        self.assertEqual(auth_failure.status_code, 401, auth_failure.text)
        self.assertEqual(auth_failure.json()["error_code"], "AUTH_INVALID_SIGNATURE")

    def test_late_success_callback_creates_reconciliation_case_and_ops_can_resolve_it(self):
        suffix = uuid4().hex[:12]
        seed = self._setup_active_merchant(suffix)
        payment = self._create_payment(seed, suffix, amount="42000.00")

        payment_row = self._payment_row(payment["transaction_id"])
        with SessionLocal() as db:
            expired_count = expiration_service.expire_overdue_payments(
                db,
                now=payment_row.expire_at + timedelta(seconds=1),
            )
            db.commit()
        self.assertGreaterEqual(expired_count, 1)
        self.assertEqual(self._payment_row(payment["transaction_id"]).status, PaymentStatus.EXPIRED)

        callback = self._mark_payment_success(payment["transaction_id"], amount="42000.00")
        self.assertEqual(callback["processing_result"], "PENDING_REVIEW")
        reconciliation_id = callback["reconciliation_record_id"]

        list_response = self.client.get("/v1/ops/reconciliation?match_result=PENDING_REVIEW")
        self.assertEqual(list_response.status_code, 200, list_response.text)
        listed_ids = {record["record_id"] for record in list_response.json()["records"]}
        self.assertIn(reconciliation_id, listed_ids)

        resolve_response = self.client.post(
            f"/v1/ops/reconciliation/{reconciliation_id}/resolve",
            json={
                **self._actor(seed["ops_user_id"], "E2E accept provider late success"),
                "reviewed_by": str(seed["ops_user_id"]),
                "review_note": "E2E accept provider late success",
            },
        )
        self.assertEqual(resolve_response.status_code, 200, resolve_response.text)
        self.assertEqual(resolve_response.json()["match_result"], "RESOLVED")

        with SessionLocal() as db:
            row = db.get(ReconciliationRecord, reconciliation_id)
            self.assertEqual(row.match_result, ReconciliationStatus.RESOLVED)

    def test_manual_webhook_retry_records_attempt_and_audit(self):
        suffix = uuid4().hex[:12]
        seed = self._setup_active_merchant(suffix)
        payment = self._create_payment(seed, suffix)
        self._mark_payment_success(payment["transaction_id"])
        event = self._latest_event("payment.succeeded")

        for _ in range(4):
            self._deliver_event(event.id, status_code=500)

        with SessionLocal() as db:
            failed_event = db.get(WebhookEvent, event.id)
            self.assertEqual(failed_event.status, WebhookEventStatus.FAILED)

        with patch(
            "app.services.webhook_delivery_service._post_webhook",
            return_value=(DeliveryAttemptResult.SUCCESS, 200, "ok", None),
        ):
            retry_response = self.client.post(
                f"/v1/ops/webhooks/{event.event_id}/retry",
                json={
                    "actor_type": "OPS",
                    "actor_id": str(seed["ops_user_id"]),
                    "reason": "E2E manual retry",
                },
            )
        self.assertEqual(retry_response.status_code, 200, retry_response.text)
        self.assertEqual(retry_response.json()["status"], "DELIVERED")

        with SessionLocal() as db:
            delivered_event = db.get(WebhookEvent, event.id)
            self.assertEqual(delivered_event.status, WebhookEventStatus.DELIVERED)
            attempt_count = db.scalar(
                select(WebhookDeliveryAttempt)
                .where(WebhookDeliveryAttempt.webhook_event_id == event.id)
                .order_by(WebhookDeliveryAttempt.attempt_no.desc())
            ).attempt_no
            self.assertEqual(attempt_count, 5)
            audit = db.scalar(
                select(AuditLog)
                .where(AuditLog.entity_id == event.id)
                .order_by(AuditLog.created_at.desc())
            )
            self.assertIsNotNone(audit)
            self.assertEqual(audit.event_type, "WEBHOOK_MANUAL_RETRY")

    def test_suspended_merchant_cannot_create_new_payments_or_refunds(self):
        suffix = uuid4().hex[:12]
        seed = self._setup_active_merchant(suffix)
        payment = self._create_payment(seed, suffix)
        self._mark_payment_success(payment["transaction_id"])

        suspend_response = self.client.post(
            f"/v1/ops/merchants/{seed['merchant_id']}/suspend",
            json=self._actor(seed["ops_user_id"], "E2E suspend merchant"),
        )
        self.assertEqual(suspend_response.status_code, 200, suspend_response.text)

        blocked_payment = self._merchant_post(
            seed,
            "/v1/payments",
            {
                "order_id": f"blocked-payment-{suffix}",
                "amount": "12345.00",
                "currency": "VND",
                "description": "E2E blocked payment",
                "ttl_seconds": 900,
            },
            idempotency_key=f"blocked-payment-{suffix}",
        )
        self.assertEqual(blocked_payment.status_code, 403, blocked_payment.text)
        self.assertEqual(blocked_payment.json()["error_code"], "MERCHANT_NOT_ACTIVE")

        blocked_refund = self._merchant_post(
            seed,
            "/v1/refunds",
            {
                "original_transaction_id": payment["transaction_id"],
                "refund_id": f"blocked-refund-{suffix}",
                "refund_amount": "12345.00",
                "reason": "E2E blocked refund",
            },
            idempotency_key=f"blocked-refund-{suffix}",
        )
        self.assertEqual(blocked_refund.status_code, 403, blocked_refund.text)
        self.assertEqual(blocked_refund.json()["error_code"], "MERCHANT_NOT_ACTIVE")


if __name__ == "__main__":
    unittest.main()
