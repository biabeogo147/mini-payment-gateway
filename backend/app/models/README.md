# Models Entity Diagram

This directory contains the core SQLAlchemy models for the mini payment gateway.
The diagram focuses on MVP entities and the relationships needed for merchant
onboarding, QR payments, refunds, webhook delivery, reconciliation, and audit.

```mermaid
erDiagram
    INTERNAL_USER {
        UUID id PK
        string email UK
        string full_name
        enum role
        enum status
        datetime created_at
        datetime updated_at
    }

    MERCHANT {
        UUID id PK
        string merchant_id UK
        string merchant_name
        string legal_name
        string contact_name
        string contact_email
        string contact_phone
        text webhook_url
        string_array allowed_ip_list
        enum status
        string settlement_account_name
        string settlement_account_number
        string settlement_bank_code
        datetime created_at
        datetime updated_at
    }

    MERCHANT_ONBOARDING_CASE {
        UUID id PK
        UUID merchant_db_id FK
        enum status
        string domain_or_app_name
        jsonb submitted_profile_json
        jsonb documents_json
        jsonb review_checks_json
        text decision_note
        UUID reviewed_by FK
        datetime reviewed_at
        datetime created_at
        datetime updated_at
    }

    MERCHANT_CREDENTIAL {
        UUID id PK
        UUID merchant_db_id FK
        string access_key UK
        text secret_key_encrypted
        string secret_key_last4
        enum status
        datetime expired_at
        datetime rotated_at
        datetime created_at
        datetime updated_at
    }

    ORDER_REFERENCE {
        UUID id PK
        UUID merchant_db_id FK
        string order_id
        string order_status_snapshot
        UUID latest_payment_transaction_id FK
        datetime created_at
        datetime updated_at
    }

    PAYMENT_TRANSACTION {
        UUID id PK
        string transaction_id UK
        UUID merchant_db_id FK
        UUID order_reference_id FK
        string order_id
        numeric amount
        string currency
        text description
        enum status
        text qr_content
        text qr_image_url
        text qr_image_base64
        string external_reference
        string idempotency_key
        datetime expire_at
        datetime paid_at
        string failed_reason_code
        text failed_reason_message
        datetime created_at
        datetime updated_at
    }

    REFUND_TRANSACTION {
        UUID id PK
        string refund_transaction_id UK
        UUID merchant_db_id FK
        UUID payment_transaction_id FK
        string refund_id
        numeric refund_amount
        text reason
        enum status
        string external_reference
        string idempotency_key
        datetime processed_at
        string failed_reason_code
        text failed_reason_message
        datetime created_at
        datetime updated_at
    }

    WEBHOOK_EVENT {
        UUID id PK
        string event_id UK
        UUID merchant_db_id FK
        string event_type
        enum entity_type
        UUID entity_id
        jsonb payload_json
        text signature
        enum status
        datetime next_retry_at
        int attempt_count
        datetime last_attempt_at
        datetime created_at
        datetime updated_at
    }

    WEBHOOK_DELIVERY_ATTEMPT {
        UUID id PK
        UUID webhook_event_id FK
        int attempt_no
        text request_url
        jsonb request_headers_json
        jsonb request_body_json
        int response_status_code
        text response_body_snippet
        text error_message
        datetime started_at
        datetime finished_at
        enum result
    }

    BANK_CALLBACK_LOG {
        UUID id PK
        enum source_type
        string external_reference
        string transaction_reference
        enum callback_type
        jsonb raw_payload_json
        string normalized_status
        datetime received_at
        datetime processed_at
        enum processing_result
        text error_message
        datetime created_at
        datetime updated_at
    }

    RECONCILIATION_RECORD {
        UUID id PK
        enum entity_type
        UUID entity_id
        string internal_status
        string external_status
        numeric internal_amount
        numeric external_amount
        enum match_result
        string mismatch_reason_code
        text mismatch_reason_message
        UUID reviewed_by FK
        text review_note
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOG {
        UUID id PK
        string event_type
        enum entity_type
        UUID entity_id
        enum actor_type
        UUID actor_id FK
        jsonb before_state_json
        jsonb after_state_json
        text reason
        datetime created_at
    }

    MERCHANT ||--|| MERCHANT_ONBOARDING_CASE : has
    MERCHANT ||--o{ MERCHANT_CREDENTIAL : owns
    MERCHANT ||--o{ ORDER_REFERENCE : owns
    MERCHANT ||--o{ PAYMENT_TRANSACTION : receives
    MERCHANT ||--o{ REFUND_TRANSACTION : owns
    MERCHANT ||--o{ WEBHOOK_EVENT : receives_events

    INTERNAL_USER ||--o{ MERCHANT_ONBOARDING_CASE : reviews
    INTERNAL_USER ||--o{ RECONCILIATION_RECORD : reviews
    INTERNAL_USER ||--o{ AUDIT_LOG : acts

    ORDER_REFERENCE ||--o{ PAYMENT_TRANSACTION : groups_attempts
    ORDER_REFERENCE o|--o| PAYMENT_TRANSACTION : latest_attempt
    PAYMENT_TRANSACTION ||--o{ REFUND_TRANSACTION : can_refund

    WEBHOOK_EVENT ||--o{ WEBHOOK_DELIVERY_ATTEMPT : attempts
```

## Important DB Invariants

- `merchants.merchant_id` is unique and is the public merchant identifier.
- `merchant_credentials` allows only one `ACTIVE` credential per merchant.
- `merchant_onboarding_cases` allows one onboarding case per merchant in the MVP.
- `order_references` is unique by `merchant_db_id + order_id`.
- `payment_transactions` allows one active `PENDING` payment per `merchant_db_id + order_id`.
- `refund_transactions` is unique by `merchant_db_id + refund_id`.
- `refund_transactions` allows at most one `REFUNDED` row per payment.
- Payment and refund amounts must be positive.
- `webhook_events.attempt_count` must be non-negative.

## Logical References

`AuditLog`, `WebhookEvent`, and `ReconciliationRecord` use `entity_type + entity_id`
to point at business entities. Those references are polymorphic by design, so they
are validated by service logic rather than by a direct database foreign key.

`BankCallbackLog` stores raw provider evidence and references gateway objects by
provider or gateway reference strings instead of strict foreign keys.
