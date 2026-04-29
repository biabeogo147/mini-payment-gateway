# 1. Main modules

## Merchant Management

Responsibilities:

* store merchant operational profile
* store and rotate merchant credentials
* store merchant onboarding case
* validate merchant operational readiness

Main entities:

* `Merchant`
* `MerchantCredential`
* `MerchantOnboardingCase`
* `AuditLog`

## Payment Service

Responsibilities:

* create payment
* enforce auth and idempotency
* create `OrderReference`
* create `PaymentTransaction`
* generate dynamic QR

Main entities:

* `Merchant`
* `MerchantCredential`
* `OrderReference`
* `PaymentTransaction`

## Refund Service

Responsibilities:

* validate refund request
* load original payment
* create `RefundTransaction`
* update refund state

Main entities:

* `Merchant`
* `PaymentTransaction`
* `RefundTransaction`

## Webhook Delivery

Responsibilities:

* create outbound event payload
* sign payload
* retry delivery
* store attempt history

Main entities:

* `WebhookEvent`
* `WebhookDeliveryAttempt`

## Reconciliation and Ops

Responsibilities:

* store callback evidence
* store mismatch records
* store audit trail

Main entities:

* `BankCallbackLog`
* `ReconciliationRecord`
* `AuditLog`

---

# 2. Core entities

## Merchant

Purpose: operational merchant profile.

Required fields:

* `id`
* `merchant_id`
* `merchant_name`
* `legal_name`
* `contact_name`
* `contact_email`
* `contact_phone`
* `webhook_url`
* `allowed_ip_list`
* `status` = `PENDING_REVIEW | ACTIVE | REJECTED | SUSPENDED | DISABLED`
* `settlement_account_name`
* `settlement_account_number`
* `settlement_bank_code`
* `created_at`
* `updated_at`

Notes:

* no `approved_at`
* no `approved_by`
* approval metadata belongs to onboarding case

## MerchantOnboardingCase

Purpose: onboarding payload, review evidence, and approval decision.

Required fields:

* `id`
* `merchant_db_id` unique
* `status` = `DRAFT | PENDING_REVIEW | APPROVED | REJECTED`
* `domain_or_app_name`
* `submitted_profile_json`
* `documents_json`
* `review_checks_json`
* `decision_note`
* `reviewed_by`
* `reviewed_at`
* `created_at`
* `updated_at`

Notes:

* one active onboarding case row per merchant in MVP
* case approval can lead to merchant activation after config is complete

## MerchantCredential

Purpose: merchant auth material.

Required fields:

* `id`
* `merchant_db_id`
* `access_key`
* `secret_key_encrypted`
* `secret_key_last4`
* `status` = `ACTIVE | INACTIVE | ROTATED`
* `expired_at`
* `rotated_at`
* `created_at`
* `updated_at`

DB rule:

* partial unique: one `ACTIVE` credential per merchant

## OrderReference

Purpose: business order mapping for payment attempts.

Required fields:

* `id`
* `merchant_db_id`
* `order_id`
* `latest_payment_transaction_id`
* `order_status_snapshot`
* `created_at`
* `updated_at`

Decision:

* this entity is required, not optional

## PaymentTransaction

Purpose: single persisted payment attempt.

Required fields:

* `id`
* `transaction_id`
* `merchant_db_id`
* `order_reference_id`
* `order_id`
* `amount`
* `currency`
* `description`
* `status` = `PENDING | SUCCESS | FAILED | EXPIRED`
* `qr_content`
* `qr_image_url` or `qr_image_base64`
* `external_reference`
* `idempotency_key`
* `expire_at`
* `paid_at`
* `failed_reason_code`
* `failed_reason_message`
* `created_at`
* `updated_at`

DB rules:

* check: amount > 0
* partial unique: one `PENDING` payment per `merchant_db_id + order_id`

## RefundTransaction

Purpose: refund flow record.

Required fields:

* `id`
* `refund_transaction_id`
* `merchant_db_id`
* `payment_transaction_id`
* `refund_id`
* `refund_amount`
* `reason`
* `status` = `REFUND_PENDING | REFUNDED | REFUND_FAILED`
* `external_reference`
* `idempotency_key`
* `processed_at`
* `failed_reason_code`
* `failed_reason_message`
* `created_at`
* `updated_at`

DB rules:

* check: refund_amount > 0
* unique: `merchant_db_id + refund_id`
* partial unique: one `REFUNDED` row per payment

## WebhookEvent

Purpose: outbound webhook business event.

Required fields:

* `id`
* `event_id`
* `merchant_db_id`
* `event_type`
* `entity_type`
* `entity_id`
* `payload_json`
* `signature`
* `status`
* `next_retry_at`
* `attempt_count`
* `last_attempt_at`
* `created_at`
* `updated_at`

DB rule:

* check: attempt_count >= 0

## WebhookDeliveryAttempt

Purpose: single HTTP send attempt for a webhook event.

## BankCallbackLog

Purpose: raw and normalized callback evidence from provider side.

## ReconciliationRecord

Purpose: mismatch or match evidence between internal and external transaction state.

## AuditLog

Purpose: immutable audit trail for manual or administrative action.

`entity_type` must support at least:

* `MERCHANT`
* `MERCHANT_CREDENTIAL`
* `ONBOARDING_CASE`
* `PAYMENT`
* `REFUND`
* `WEBHOOK_EVENT`
* `RECONCILIATION`
