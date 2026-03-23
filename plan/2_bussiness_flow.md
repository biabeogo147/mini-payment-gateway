# 1. Merchant onboarding flow

## Goal

Move a merchant from review state to operational state in a controlled internal workflow.

## Actors

* Merchant: provides profile and integration details
* Ops/Admin: reviews and decides
* Gateway: stores merchant, onboarding case, and credentials

## Inputs

Merchant data captured in onboarding case:

* merchant name and legal name
* contact name, email, phone
* settlement account info
* webhook URL
* allowed IP list
* domain or app name
* legal/supporting documents metadata

Review data captured by ops:

* review checklist result
* settlement verification result
* webhook validation result
* IP whitelist validation result
* approval or rejection note

## Source of truth

* `MerchantOnboardingCase` stores onboarding payload, documents, review checks, and approval metadata
* `Merchant` stores operational profile and operational status
* `MerchantCredential` stores active and rotated credentials

## Flow

1. Ops creates `Merchant` with status `PENDING_REVIEW`
2. Ops creates or updates `MerchantOnboardingCase`
3. Ops reviews submitted profile, documents, settlement data, and webhook config
4. Ops updates onboarding case status to `APPROVED` or `REJECTED`
5. If approved and config is complete, gateway issues credentials
6. Merchant status moves to `ACTIVE`
7. Ops can later move merchant to `SUSPENDED` or `DISABLED`

## Business rules

* approval metadata is stored on onboarding case, not on merchant
* merchant becomes `ACTIVE` only after onboarding case is `APPROVED` and credentials exist
* `SUSPENDED` merchant can be searched and inspected but cannot create new payment or refund
* one active onboarding case record exists per merchant in MVP

---

# 2. Payment flow

## Goal

Create a usable payment record, generate dynamic QR, wait for result, and notify merchant.

## Input

* merchant auth headers
* `order_id`
* `amount`
* `description`
* `expire_at` or TTL
* optional metadata

## Output

* `transaction_id`
* `order_id`
* `merchant_id`
* `qr_content`
* optional QR image field
* `status = PENDING`
* `expire_at`

## Canonical states

Persisted DB states:

* `PENDING`
* `SUCCESS`
* `FAILED`
* `EXPIRED`

`INITIATED` is not persisted. If create-payment fails before the transaction is usable, the API returns an error and no transaction row is kept.

## Flow

1. Verify merchant and signature
2. Enforce idempotency by `merchant_id + order_id`
3. Load or create required `OrderReference`
4. Create `PaymentTransaction` directly in `PENDING`
5. Generate dynamic QR
6. Return QR payload to merchant
7. Receive provider callback or simulator result
8. Move transaction to `SUCCESS`, `FAILED`, or `EXPIRED`
9. Emit webhook event

## Rules

* one active payment per `merchant_id + order_id`
* active payment means `PENDING`
* expired payment does not revive
* `SUCCESS` is final for payment flow
* only `SUCCESS` payment is refund-eligible

---

# 3. Refund flow

## Goal

Handle refund as a separate business flow with separate state machine.

## Input

* merchant auth headers
* `original_transaction_id` or `order_id`
* `refund_id`
* `refund_amount`
* `reason`

## Output

* `refund_transaction_id`
* `original_transaction_id`
* `refund_id`
* `refund_amount`
* `refund_status`

## States

* `REFUND_PENDING`
* `REFUNDED`
* `REFUND_FAILED`

## Flow

1. Verify merchant and signature
2. Load original payment
3. Validate refund rules
4. Enforce idempotency by `merchant_id + refund_id`
5. Create `RefundTransaction`
6. Process refund through provider or simulator
7. Update refund status
8. Emit refund webhook event

## Rules

* only `SUCCESS` payment can be refunded
* full refund only in MVP
* refund window = 7 days from `paid_at`
* unique logical refund by `merchant_id + refund_id`
* DB also blocks more than one `REFUNDED` row for the same payment

---

# 4. Reconciliation flow

## Goal

Detect mismatch between gateway data and provider data, then support manual review.

## Flow

1. Collect internal payment/refund records
2. Collect provider-side result data
3. Compare status, amount, and reference
4. Store `ReconciliationRecord`
5. Route mismatch to ops review
6. Keep audit trail for manual intervention

---

# 5. Failure handling and query fallback

## Main patterns

* delayed callback: keep waiting until timeout or reconcile later
* duplicate create payment: return existing `PENDING` payment when request is semantically identical
* duplicate refund request: return existing refund for same `merchant_id + refund_id`
* webhook delivery failure: retry automatically, then expose for manual retry
* merchant status query remains the fallback when webhook or callback is delayed
