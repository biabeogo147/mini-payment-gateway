from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/mini_payment_gateway",
)


def scalar_uuid(connection, sql: str, params: dict) -> str:
    return str(connection.execute(text(sql), params).scalar_one())


def main() -> None:
    engine = create_engine(DATABASE_URL, future=True)

    with engine.begin() as connection:
        connection.execute(text("DELETE FROM audit_logs"))
        connection.execute(text("DELETE FROM reconciliation_records"))
        connection.execute(text("DELETE FROM bank_callback_logs"))
        connection.execute(text("DELETE FROM webhook_delivery_attempts"))
        connection.execute(text("DELETE FROM webhook_events"))
        connection.execute(text("DELETE FROM refund_transactions"))
        connection.execute(text("DELETE FROM payment_transactions"))
        connection.execute(text("DELETE FROM order_references"))
        connection.execute(text("DELETE FROM merchant_credentials"))
        connection.execute(text("DELETE FROM merchants"))
        connection.execute(text("DELETE FROM internal_users"))

        admin_id = scalar_uuid(
            connection,
            """
            INSERT INTO internal_users (email, full_name, role, status)
            VALUES (:email, :full_name, :role, :status)
            RETURNING id
            """,
            {
                "email": "ops@example.com",
                "full_name": "Ops User",
                "role": "OPS",
                "status": "ACTIVE",
            },
        )

        merchant_uuid = scalar_uuid(
            connection,
            """
            INSERT INTO merchants (
              merchant_id, merchant_name, legal_name, contact_name, contact_email,
              contact_phone, webhook_url, allowed_ip_list, status,
              settlement_account_name, settlement_account_number, settlement_bank_code,
              approved_at, approved_by
            )
            VALUES (
              :merchant_id, :merchant_name, :legal_name, :contact_name, :contact_email,
              :contact_phone, :webhook_url, :allowed_ip_list, :status,
              :settlement_account_name, :settlement_account_number, :settlement_bank_code,
              :approved_at, :approved_by
            )
            RETURNING id
            """,
            {
                "merchant_id": "mrc_demo_001",
                "merchant_name": "Demo Merchant",
                "legal_name": "Demo Merchant LLC",
                "contact_name": "Merchant Admin",
                "contact_email": "merchant@example.com",
                "contact_phone": "0123456789",
                "webhook_url": "https://merchant.test/webhook",
                "allowed_ip_list": ["127.0.0.1"],
                "status": "ACTIVE",
                "settlement_account_name": "Demo Settlement",
                "settlement_account_number": "123456789",
                "settlement_bank_code": "VCB",
                "approved_at": datetime.now(timezone.utc),
                "approved_by": admin_id,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO merchant_credentials (
                  merchant_db_id, access_key, secret_key_encrypted, secret_key_last4, status
                )
                VALUES (:merchant_db_id, :access_key, :secret_key_encrypted, :secret_key_last4, :status)
                """
            ),
            {
                "merchant_db_id": merchant_uuid,
                "access_key": "acc_demo_001",
                "secret_key_encrypted": "encrypted-secret-value",
                "secret_key_last4": "1234",
                "status": "ACTIVE",
            },
        )

        order_reference_id = scalar_uuid(
            connection,
            """
            INSERT INTO order_references (merchant_db_id, order_id)
            VALUES (:merchant_db_id, :order_id)
            RETURNING id
            """,
            {
                "merchant_db_id": merchant_uuid,
                "order_id": "order_001",
            },
        )

        payment_id = scalar_uuid(
            connection,
            """
            INSERT INTO payment_transactions (
              transaction_id, merchant_db_id, order_reference_id, order_id,
              amount, currency, description, status, qr_content, expire_at, idempotency_key
            )
            VALUES (
              :transaction_id, :merchant_db_id, :order_reference_id, :order_id,
              :amount, :currency, :description, :status, :qr_content, :expire_at, :idempotency_key
            )
            RETURNING id
            """,
            {
                "transaction_id": "txn_demo_001",
                "merchant_db_id": merchant_uuid,
                "order_reference_id": order_reference_id,
                "order_id": "order_001",
                "amount": Decimal("125000.00"),
                "currency": "VND",
                "description": "Demo order",
                "status": "PENDING",
                "qr_content": "000201010212...",
                "expire_at": datetime.now(timezone.utc) + timedelta(minutes=15),
                "idempotency_key": "idem_payment_001",
            },
        )

        connection.execute(
            text(
                """
                UPDATE order_references
                SET latest_payment_transaction_id = :payment_id
                WHERE id = :order_reference_id
                """
            ),
            {
                "payment_id": payment_id,
                "order_reference_id": order_reference_id,
            },
        )

        duplicate_payment_rejected = False
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO payment_transactions (
                      transaction_id, merchant_db_id, order_reference_id, order_id,
                      amount, currency, description, status, qr_content, expire_at
                    )
                    VALUES (
                      :transaction_id, :merchant_db_id, :order_reference_id, :order_id,
                      :amount, :currency, :description, :status, :qr_content, :expire_at
                    )
                    """
                ),
                {
                    "transaction_id": "txn_demo_002",
                    "merchant_db_id": merchant_uuid,
                    "order_reference_id": order_reference_id,
                    "order_id": "order_001",
                    "amount": Decimal("125000.00"),
                    "currency": "VND",
                    "description": "Duplicate pending payment",
                    "status": "PENDING",
                    "qr_content": "duplicate",
                    "expire_at": datetime.now(timezone.utc) + timedelta(minutes=15),
                },
            )
        except Exception:
            duplicate_payment_rejected = True

        if not duplicate_payment_rejected:
            raise RuntimeError("Expected duplicate active payment insert to fail.")

        connection.execute(
            text(
                """
                UPDATE payment_transactions
                SET status = 'SUCCESS', paid_at = :paid_at
                WHERE id = :payment_id
                """
            ),
            {
                "payment_id": payment_id,
                "paid_at": datetime.now(timezone.utc),
            },
        )

        refund_id = scalar_uuid(
            connection,
            """
            INSERT INTO refund_transactions (
              refund_transaction_id, merchant_db_id, payment_transaction_id,
              refund_id, refund_amount, reason, status, idempotency_key
            )
            VALUES (
              :refund_transaction_id, :merchant_db_id, :payment_transaction_id,
              :refund_id, :refund_amount, :reason, :status, :idempotency_key
            )
            RETURNING id
            """,
            {
                "refund_transaction_id": "rtxn_demo_001",
                "merchant_db_id": merchant_uuid,
                "payment_transaction_id": payment_id,
                "refund_id": "refund_001",
                "refund_amount": Decimal("125000.00"),
                "reason": "Customer cancelled",
                "status": "REFUND_PENDING",
                "idempotency_key": "idem_refund_001",
            },
        )

        duplicate_refund_rejected = False
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO refund_transactions (
                      refund_transaction_id, merchant_db_id, payment_transaction_id,
                      refund_id, refund_amount, reason, status
                    )
                    VALUES (
                      :refund_transaction_id, :merchant_db_id, :payment_transaction_id,
                      :refund_id, :refund_amount, :reason, :status
                    )
                    """
                ),
                {
                    "refund_transaction_id": "rtxn_demo_002",
                    "merchant_db_id": merchant_uuid,
                    "payment_transaction_id": payment_id,
                    "refund_id": "refund_001",
                    "refund_amount": Decimal("125000.00"),
                    "reason": "Duplicate refund id",
                    "status": "REFUND_PENDING",
                },
            )
        except Exception:
            duplicate_refund_rejected = True

        if not duplicate_refund_rejected:
            raise RuntimeError("Expected duplicate refund_id insert to fail.")

        webhook_event_id = scalar_uuid(
            connection,
            """
            INSERT INTO webhook_events (
              event_id, merchant_db_id, event_type, entity_type, entity_id, payload_json,
              signature, status, next_retry_at, attempt_count
            )
            VALUES (
              :event_id, :merchant_db_id, :event_type, :entity_type, :entity_id, CAST(:payload_json AS jsonb),
              :signature, :status, :next_retry_at, :attempt_count
            )
            RETURNING id
            """,
            {
                "event_id": "evt_001",
                "merchant_db_id": merchant_uuid,
                "event_type": "PAYMENT_SUCCESS",
                "entity_type": "PAYMENT",
                "entity_id": payment_id,
                "payload_json": '{"transaction_id":"txn_demo_001","status":"SUCCESS"}',
                "signature": "sig_001",
                "status": "PENDING",
                "next_retry_at": datetime.now(timezone.utc) + timedelta(minutes=1),
                "attempt_count": 0,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO webhook_delivery_attempts (
                  webhook_event_id, attempt_no, request_url, request_headers_json,
                  request_body_json, response_status_code, response_body_snippet,
                  error_message, started_at, finished_at, result
                )
                VALUES (
                  :webhook_event_id, :attempt_no, :request_url, CAST(:request_headers_json AS jsonb),
                  CAST(:request_body_json AS jsonb), :response_status_code, :response_body_snippet,
                  :error_message, :started_at, :finished_at, :result
                )
                """
            ),
            {
                "webhook_event_id": webhook_event_id,
                "attempt_no": 1,
                "request_url": "https://merchant.test/webhook",
                "request_headers_json": '{"X-Signature":"sig_001"}',
                "request_body_json": '{"transaction_id":"txn_demo_001","status":"SUCCESS"}',
                "response_status_code": 500,
                "response_body_snippet": "internal error",
                "error_message": "webhook failed",
                "started_at": datetime.now(timezone.utc),
                "finished_at": datetime.now(timezone.utc),
                "result": "FAILED",
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO bank_callback_logs (
                  source_type, external_reference, transaction_reference, callback_type,
                  raw_payload_json, normalized_status, received_at, processed_at,
                  processing_result, error_message
                )
                VALUES (
                  :source_type, :external_reference, :transaction_reference, :callback_type,
                  CAST(:raw_payload_json AS jsonb), :normalized_status, :received_at, :processed_at,
                  :processing_result, :error_message
                )
                """
            ),
            {
                "source_type": "SIMULATOR",
                "external_reference": "ext_001",
                "transaction_reference": "txn_demo_001",
                "callback_type": "PAYMENT_RESULT",
                "raw_payload_json": '{"external_reference":"ext_001","status":"SUCCESS"}',
                "normalized_status": "SUCCESS",
                "received_at": datetime.now(timezone.utc),
                "processed_at": datetime.now(timezone.utc),
                "processing_result": "PROCESSED",
                "error_message": None,
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO reconciliation_records (
                  entity_type, entity_id, internal_status, external_status,
                  internal_amount, external_amount, match_result,
                  mismatch_reason_code, mismatch_reason_message, reviewed_by, review_note
                )
                VALUES (
                  :entity_type, :entity_id, :internal_status, :external_status,
                  :internal_amount, :external_amount, :match_result,
                  :mismatch_reason_code, :mismatch_reason_message, :reviewed_by, :review_note
                )
                """
            ),
            {
                "entity_type": "PAYMENT",
                "entity_id": payment_id,
                "internal_status": "SUCCESS",
                "external_status": "SUCCESS",
                "internal_amount": Decimal("125000.00"),
                "external_amount": Decimal("125000.00"),
                "match_result": "MATCHED",
                "mismatch_reason_code": None,
                "mismatch_reason_message": None,
                "reviewed_by": admin_id,
                "review_note": "Auto-matched in smoke check",
            },
        )

        connection.execute(
            text(
                """
                INSERT INTO audit_logs (
                  event_type, entity_type, entity_id, actor_type, actor_id,
                  before_state_json, after_state_json, reason
                )
                VALUES (
                  :event_type, :entity_type, :entity_id, :actor_type, :actor_id,
                  CAST(:before_state_json AS jsonb), CAST(:after_state_json AS jsonb), :reason
                )
                """
            ),
            {
                "event_type": "WEBHOOK_RETRIED_MANUALLY",
                "entity_type": "WEBHOOK_EVENT",
                "entity_id": webhook_event_id,
                "actor_type": "OPS",
                "actor_id": admin_id,
                "before_state_json": '{"status":"FAILED"}',
                "after_state_json": '{"status":"PENDING"}',
                "reason": "Smoke verification log",
            },
        )

        expected_indexes = {
            "ix_merchants_merchant_id",
            "ux_merchant_credentials_active_per_merchant",
            "ux_payment_transactions_active_order",
            "ix_payment_transactions_transaction_id",
            "ix_payment_transactions_merchant_order",
            "ix_refund_transactions_refund_id",
            "ix_webhook_events_merchant_status_retry",
            "ix_reconciliation_records_match_result",
        }

        present_indexes = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = current_schema()
                    """
                )
            )
        }
        missing_indexes = expected_indexes - present_indexes
        if missing_indexes:
            raise RuntimeError(f"Missing expected indexes: {sorted(missing_indexes)}")

        print("Smoke verification passed.")
        print(f"Merchant UUID: {merchant_uuid}")
        print(f"Payment UUID: {payment_id}")
        print(f"Refund UUID: {refund_id}")


if __name__ == "__main__":
    main()
